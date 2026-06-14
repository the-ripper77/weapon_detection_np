from flask import Flask, render_template, Response, jsonify, request
import time
import os
import cv2
import numpy as np
import base64
from flask_sock import Sock
import threading

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
sock = Sock(app)

# Global registry of active viewer sockets
view_sockets = []
view_sockets_lock = threading.Lock()


@sock.route('/ws/upload')
def ws_upload(ws):
    """Receive raw binary JPEG frames from mobile browser via WebSocket."""
    from detection import Detection
    try:
        while True:
            frame_bytes = ws.receive()
            if not frame_bytes:
                break
            with Detection.uploaded_frame_lock:
                Detection.uploaded_frame = frame_bytes
    except Exception as e:
        pass


@sock.route('/ws/view')
def ws_view(ws):
    """Provide real-time binary JPEG frame updates to web client via WebSocket."""
    with view_sockets_lock:
        view_sockets.append(ws)
    try:
        while True:
            data = ws.receive(timeout=10)
            if data is None:
                break
    except Exception:
        pass
    finally:
        with view_sockets_lock:
            if ws in view_sockets:
                view_sockets.remove(ws)


class AppState:
    location = "Not Configured"
    contact = "Not Configured"
    class_name = "object"
    running = False
    source_type = "webcam"   # "webcam", "cctv", "mobile"
    ngrok_url = None


def gen_placeholder():
    """Generate a sleek dark placeholder frame when detection is inactive."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    for i in range(0, 480, 30):
        cv2.line(img, (0, i), (640, i), (15, 20, 30), 1)
    for i in range(0, 640, 30):
        cv2.line(img, (i, 0), (i, 480), (15, 20, 30), 1)
    cv2.putText(img, "MONITORING INACTIVE", (140, 220),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 200), 2, cv2.LINE_AA)
    cv2.putText(img, "Waiting for stream to start...", (165, 260),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 110, 130), 1, cv2.LINE_AA)
    _, buffer = cv2.imencode('.jpg', img)
    return buffer.tobytes()


def gen_frames():
    """MJPEG generator from the latest annotated frame."""
    from detection import Detection
    placeholder = None

    while True:
        frame = None
        if AppState.running:
            with Detection.frame_lock:
                frame = Detection.latest_frame

        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            if placeholder is None:
                placeholder = gen_placeholder()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + placeholder + b'\r\n')
        time.sleep(0.04)  # ~25 FPS


@app.route('/')
def index():
    mode = request.args.get('mode', 'viewer')
    return render_template(
        'index.html',
        location=AppState.location,
        contact=AppState.contact,
        mode=mode
    )


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/upload_frame', methods=['POST'])
def upload_frame():
    """Receive a base64-encoded JPEG frame from mobile browser and buffer it."""
    from detection import Detection
    try:
        data = request.get_json()
        if data and 'frame' in data:
            # Strip data URI prefix if present (data:image/jpeg;base64,...)
            b64_data = data['frame']
            if ',' in b64_data:
                b64_data = b64_data.split(',', 1)[1]
            frame_bytes = base64.b64decode(b64_data)
            with Detection.uploaded_frame_lock:
                Detection.uploaded_frame = frame_bytes
            return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error processing uploaded frame: {e}")
    return jsonify({'status': 'error'}), 400


@app.route('/status')
def status():
    return jsonify({
        'running': AppState.running,
        'location': AppState.location,
        'contact': AppState.contact,
        'class_name': AppState.class_name,
        'source_type': AppState.source_type,
    })


def run_server():
    app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)

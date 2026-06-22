from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QImage
import cv2
import os
import time
import threading
from datetime import datetime
from web_server import AppState

class Detection(QThread):
    changePixmap = pyqtSignal(QImage)
    playAlert = pyqtSignal()
    latest_frame = None
    frame_lock = threading.Lock()

    # Mobile frame upload buffer
    uploaded_frame = None
    uploaded_frame_lock = threading.Lock()

    def __init__(self):
        super(Detection, self).__init__()
        self.running = False
        self.model = None
        self.class_name = 'object'
        self.box_color = (0, 0, 255)
        self.model_attempted = False
        self.source_type = "webcam"   # "webcam", "cctv", "mobile"
        self.rtsp_url = ""
        self.last_save_time = 0
        self.save_interval = 2.0  # Save at most once every 2 seconds to avoid spam
        self.last_alert_time = 0
        self.alert_cooldown = 4.0  # Cooldown in seconds to prevent overlapping audio playback
        self.device = "cpu"

    def load_model(self):
        """Load the trained YOLO model from the weights folder."""
        if self.model_attempted:
            return
        self.model_attempted = True
        try:
            from ultralytics import YOLO
        except ImportError as e:
            print(f"Ultralytics import failed: {e}")
            return
        except OSError as e:
            print(f"PyTorch/Ultralytics DLL load failed: {e}")
            return

        model_path = os.path.join(os.path.dirname(__file__), 'weights', 'best.pt')
        if not os.path.exists(model_path):
            print(f"Error: Model file not found at {model_path}")
            return

        # Detect device
        self.device = 'cpu'
        try:
            import torch
            if torch.cuda.is_available():
                self.device = '0'
                print("CUDA GPU acceleration detected and enabled!")
            else:
                print("CUDA GPU not available. Using CPU for inference.")
        except Exception:
            print("Could not import torch/check CUDA. Using CPU for inference.")

        try:
            self.model = YOLO(model_path)
            names = getattr(self.model, 'names', None)
            if isinstance(names, (list, tuple)) and len(names) > 0:
                self.class_name = names[0]
            elif isinstance(names, dict) and 0 in names:
                self.class_name = names[0]
            elif isinstance(names, dict):
                self.class_name = next(iter(names.values()), 'object')
            print(f"Model loaded successfully from {model_path} on {self.device}")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None

    def get_class_name(self, cls_id):
        """Safely retrieve the class name from model names list/dict."""
        if self.model and hasattr(self.model, 'names'):
            names = self.model.names
            if isinstance(names, dict):
                return names.get(int(cls_id), self.class_name)
            elif isinstance(names, (list, tuple)) and 0 <= int(cls_id) < len(names):
                return names[int(cls_id)]
        return self.class_name

    def _annotate_frame(self, frame, boxes, confs, clss):
        """Draw bounding boxes and labels on a frame."""
        annotated = frame.copy()
        if len(boxes) > 0:
            for i in range(len(boxes)):
                confidence = float(confs[i]) if i < len(confs) else 0.0
                cls_id = int(clss[i]) if i < len(clss) else 0
                cls_name = self.get_class_name(cls_id)
                x1, y1, x2, y2 = map(int, boxes[i])
                cv2.rectangle(annotated, (x1, y1), (x2, y2), self.box_color, 2)
                label = f"{cls_name}: {confidence:.2f}"
                cv2.rectangle(annotated, (x1, y1 - 18), (x1 + 95, y1), self.box_color, -1)
                cv2.putText(annotated, label, (x1 + 2, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        return annotated

    def _save_high_confidence_frame(self, frame, confs, clss):
        """Save frame if any detection has confidence >= 50%."""
        if not getattr(AppState, 'alerts_enabled', False):
            return

        current_time = time.time()
        
        # Check if enough time has passed since last save
        if current_time - self.last_save_time < self.save_interval:
            return
        
        # Trigger alert if any detection confidence >= 50%
        detected_objects = []
        if len(confs) > 0 and len(clss) > 0:
            for i, conf in enumerate(confs):
                if float(conf) >= 0.50:
                    cls_id = int(clss[i]) if i < len(clss) else 0
                    cls_name = self.get_class_name(cls_id)
                    detected_objects.append(cls_name)
        
        has_sufficient_confidence = len(detected_objects) > 0
        object_detected_str = ", ".join(set(detected_objects)) if detected_objects else "unknown"
        
        if has_sufficient_confidence:
            # Use the specified alert_img directory
            alert_img_dir = r"C:\Users\user\OneDrive\Desktop\Cilent Side\alert_img"
            os.makedirs(alert_img_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"detection_{timestamp}.jpg"
            filepath = os.path.join(alert_img_dir, filename)
            
            # Save the frame
            cv2.imwrite(filepath, frame)
            print(f"Saved high-confidence detection to: {filepath}")
            self.last_save_time = current_time

            # Play alert sound (with cooldown to avoid overlapping audio)
            if current_time - self.last_alert_time >= self.alert_cooldown:
                self.last_alert_time = current_time
                self.playAlert.emit()
                
            # Send alert to FastAPI Dashboard in background to prevent blocking
            import threading
            def send_alert():
                try:
                    import requests
                    import uuid
                    url = "http://localhost:8000/api/alerts"
                    
                    # Generate a short Hash/Slug (e.g., a1b2c3d4)
                    hash_slug = uuid.uuid4().hex[:8]
                    
                    data = {
                        "hash_id": hash_slug,
                        "camera_source": self.source_type,
                        "location": AppState.location,
                        "object_detected": object_detected_str,
                        "alert_sent_to": AppState.contact
                    }
                    with open(filepath, "rb") as f:
                        files = {"image": (filename, f, "image/jpeg")}
                        response = requests.post(url, data=data, files=files, timeout=30)
                    
                    if response.status_code == 200:
                        print("Alert sent to dashboard successfully.")
                        # Remove temporary local file since the dashboard handles storage (Cloud or Local)
                        try:
                            import os
                            os.remove(filepath)
                        except Exception as e:
                            print(f"Failed to clean up temp file: {e}")
                    else:
                        print(f"Failed to send alert to dashboard: {response.text}")
                except Exception as e:
                    print(f"Error sending alert to dashboard: {e}")
            
            threading.Thread(target=send_alert, daemon=True).start()


    def _emit_frame(self, annotated_frame):
        """Share frame with web server and emit PyQt6 signal."""
        # Web server frame buffer
        try:
            _, jpeg_buffer = cv2.imencode('.jpg', annotated_frame)
            frame_bytes = jpeg_buffer.tobytes()
            with Detection.frame_lock:
                Detection.latest_frame = frame_bytes
            AppState.class_name = self.class_name

            # Broadcast to active WebSockets
            from web_server import view_sockets, view_sockets_lock
            with view_sockets_lock:
                for ws in list(view_sockets):
                    try:
                        ws.send(frame_bytes)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Error encoding/broadcasting frame for web: {e}")

        # PyQt6 signal for the desktop window
        height, width, channels = annotated_frame.shape
        rgbImage = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        bytesPerLine = channels * width
        convertToQtFormat = QImage(rgbImage.data, width, height, bytesPerLine, QImage.Format.Format_RGB888)
        p = convertToQtFormat.copy()
        self.changePixmap.emit(p)

    def run_webcam_or_rtsp(self):
        """Run detection from webcam (index 0) or RTSP URL."""
        if self.source_type == "cctv" and self.rtsp_url:
            cap = cv2.VideoCapture(self.rtsp_url)
            print(f"Connecting to RTSP stream: {self.rtsp_url}")
        else:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not cap.isOpened():
            print("Error: Could not open video capture device.")
            return

        boxes, confs, clss = [], [], []
        frame_count = 0
        prev_time = time.time()

        while self.running:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame, retrying...")
                time.sleep(0.05)
                continue

            frame_count += 1
            annotated_frame = frame.copy()

            if self.model is None:
                self.load_model()

            if self.model is not None and frame_count % 3 == 0:
                try:
                    results = self.model(frame, imgsz=480, conf=0.40, device=self.device, verbose=False)
                    prediction = results[0]
                    raw_boxes = prediction.boxes.xyxy.cpu().numpy() if hasattr(prediction.boxes, 'xyxy') else []
                    raw_confs = prediction.boxes.conf.cpu().numpy() if hasattr(prediction.boxes, 'conf') else []
                    raw_clss = prediction.boxes.cls.cpu().numpy() if hasattr(prediction.boxes, 'cls') else []
                    
                    target = getattr(AppState, 'target_class', 'all')
                    if target != 'all':
                        boxes, confs, clss = [], [], []
                        for i in range(len(raw_boxes)):
                            cls_id = int(raw_clss[i]) if i < len(raw_clss) else 0
                            cls_name = self.get_class_name(cls_id)
                            if cls_name.lower() == target.lower():
                                boxes.append(raw_boxes[i])
                                confs.append(raw_confs[i])
                                clss.append(raw_clss[i])
                    else:
                        boxes, confs, clss = raw_boxes, raw_confs, raw_clss
                except Exception as e:
                    print(f"Error during inference: {e}")
                    boxes, confs, clss = [], [], []

            annotated_frame = self._annotate_frame(frame, boxes, confs, clss)

            # Save frame if confidence > 50%
            self._save_high_confidence_frame(annotated_frame, confs, clss)

            current_time = time.time()
            fps = 1 / (current_time - prev_time) if (current_time - prev_time) > 0 else 0
            prev_time = current_time
            cv2.putText(annotated_frame, f"FPS: {int(fps)}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            self._emit_frame(annotated_frame)

        cap.release()

    def run_mobile(self):
        """Run detection on frames uploaded from mobile browser."""
        print("Mobile mode: waiting for phone to connect and upload frames...")
        boxes, confs, clss = [], [], []
        frame_count = 0
        prev_time = time.time()

        while self.running:
            # Wait for an uploaded frame from the mobile browser
            frame = None
            with Detection.uploaded_frame_lock:
                if Detection.uploaded_frame is not None:
                    import numpy as np
                    buf = np.frombuffer(Detection.uploaded_frame, dtype=np.uint8)
                    frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
                    Detection.uploaded_frame = None  # Consume frame and clear buffer

            if frame is None:
                time.sleep(0.05)
                continue

            frame_count += 1

            if self.model is None:
                self.load_model()

            if self.model is not None and frame_count % 3 == 0:
                try:
                    results = self.model(frame, imgsz=320, conf=0.40, device=self.device, verbose=False)
                    prediction = results[0]
                    raw_boxes = prediction.boxes.xyxy.cpu().numpy() if hasattr(prediction.boxes, 'xyxy') else []
                    raw_confs = prediction.boxes.conf.cpu().numpy() if hasattr(prediction.boxes, 'conf') else []
                    raw_clss = prediction.boxes.cls.cpu().numpy() if hasattr(prediction.boxes, 'cls') else []
                    
                    target = getattr(AppState, 'target_class', 'all')
                    if target != 'all':
                        boxes, confs, clss = [], [], []
                        for i in range(len(raw_boxes)):
                            cls_id = int(raw_clss[i]) if i < len(raw_clss) else 0
                            cls_name = self.get_class_name(cls_id)
                            if cls_name.lower() == target.lower():
                                boxes.append(raw_boxes[i])
                                confs.append(raw_confs[i])
                                clss.append(raw_clss[i])
                    else:
                        boxes, confs, clss = raw_boxes, raw_confs, raw_clss
                except Exception as e:
                    print(f"Error during mobile inference: {e}")
                    boxes, confs, clss = [], [], []

            annotated_frame = self._annotate_frame(frame, boxes, confs, clss)

            # Save frame if confidence > 50%
            self._save_high_confidence_frame(annotated_frame, confs, clss)

            current_time = time.time()
            fps = 1 / (current_time - prev_time) if (current_time - prev_time) > 0 else 0
            prev_time = current_time
            cv2.putText(annotated_frame, f"FPS: {int(fps)}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            self._emit_frame(annotated_frame)

    def run(self):
        self.running = True
        if self.source_type == "mobile":
            self.run_mobile()
        else:
            self.run_webcam_or_rtsp()

from PyQt6.QtWidgets import QApplication
import sys
from login_window import LoginWindow
from dotenv import load_dotenv
import threading
from web_server import run_server, AppState
import os

# Load dotenv configuration
load_dotenv()

# Start the Flask web server in a daemon thread
flask_thread = threading.Thread(target=run_server, daemon=True)
flask_thread.start()

# Start the Ngrok tunnel in a background thread if an authtoken is configured
def start_ngrok():
    authtoken = os.getenv("NGROK_AUTHTOKEN")
    if not authtoken:
        print("NGROK_AUTHTOKEN not configured in .env. Running in local-only mode.")
        AppState.ngrok_url = None
        return

    try:
        from pyngrok import ngrok, conf
        ngrok.set_auth_token(authtoken)
        # Force HTTPS tunnel — required for getUserMedia camera API on mobile browsers
        tunnel = ngrok.connect(5000, bind_tls=True)
        public_url = tunnel.public_url
        # Normalize to https://
        if public_url.startswith("http://"):
            public_url = "https://" + public_url[7:]
        print("\n" + "="*55)
        print(f"  NGROK TUNNEL ACTIVE!")
        print(f"  Public URL : {public_url}")
        print(f"  Camera URL : {public_url}?mode=camera")
        print("="*55 + "\n")
        AppState.ngrok_url = public_url
    except Exception as e:
        print(f"Failed to initialize ngrok tunnel: {e}")
        AppState.ngrok_url = None

ngrok_thread = threading.Thread(target=start_ngrok, daemon=True)
ngrok_thread.start()

app = QApplication(sys.argv)
mainwidow = LoginWindow()

try:
    sys.exit(app.exec())
except:
    print("Exiting")
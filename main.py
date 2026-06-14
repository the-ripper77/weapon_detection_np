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
    use_ngrok = os.getenv("USE_NGROK", "true").lower() in ("true", "1", "yes")
    if not use_ngrok:
        print("NGROK is disabled in .env. Running in local-only mode.")
        AppState.ngrok_url = None
        return

    authtoken = os.getenv("NGROK_AUTHTOKEN")
    if not authtoken:
        print("NGROK_AUTHTOKEN not configured in .env. Running in local-only mode.")
        AppState.ngrok_url = None
        return

    try:
        import ngrok
        # Start tunnel to port 5000 using the official ngrok SDK
        listener = ngrok.forward(5000, authtoken=authtoken)
        public_url = listener.url()
        # Normalize to https://
        if public_url.startswith("http://") and not public_url.startswith("https://"):
            public_url = "https://" + public_url[7:]
        print("\n" + "="*55)
        print(f"  NGROK TUNNEL ACTIVE!")
        print(f"  Public URL : {public_url}")
        print(f"  Camera URL : {public_url}?mode=camera")
        print("="*55 + "\n")
        AppState.ngrok_url = public_url
        
        # Keep the listener alive by keeping this thread running
        import time
        while True:
            time.sleep(1)
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
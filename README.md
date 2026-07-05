# Threat Monitor

Threat Monitor is a real-time weapon detection and alerting system with a desktop GUI, a live web viewer, and an alert dashboard. It uses PyQt6 for the desktop client, OpenCV and Ultralytics YOLO for inference, Flask for live streaming/mobile upload support, and a FastAPI dashboard for alert storage and notifications.

## What this project includes

- Desktop monitoring UI for webcam, CCTV/RTSP, or mobile camera input
- Real-time object detection using a trained YOLO model
- Live web-based preview and remote access support
- Optional QR-code sharing for mobile viewing
- Alert snapshots saved locally or uploaded to cloud storage
- Email notifications for detected events
- Optional ngrok tunneling for public access

## Project structure

- main.py: launches the desktop app and starts the Flask server/ngrok tunnel
- detection.py: detection worker, video processing, model loading, alert handling
- settings_window.py: configuration window for camera source, alerts, location, and contact
- web_server.py: Flask app with streaming and upload endpoints
- detection_window.py: desktop detection window UI
- alert_dashboard/: FastAPI dashboard for alert management and image storage
- UI/: PyQt UI files
- weights/best.pt: trained detection model

## Requirements

- Python 3.10+
- Windows recommended for the desktop GUI workflow
- Internet access is helpful for installing dependencies and enabling ngrok/cloud features

## Installation

From the project root, create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the main application dependencies:

```powershell
python -m pip install --upgrade pip
pip cache purge
pip install -r requirements.txt --no-cache-dir
```

Install the dashboard dependencies:

```powershell
pip install -r alert_dashboard\requirements.txt
```

## Configuration

Copy the sample environment values from env.txt and fill them in as needed.

Key settings include:

- NGROK_AUTHTOKEN: optional ngrok auth token for public access
- USE_NGROK: set to true/false to enable or disable tunneling
- EMAIL_HOST / EMAIL_PORT / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD: SMTP configuration for email alerts
- CLOUDINARY_CLOUD_NAME / CLOUDINARY_UPLOAD_PRESET: optional cloud storage for alert images

## Running the app

Start the desktop application:

```powershell
python main.py
```

Start the alert dashboard in a second terminal:

```powershell
python alert_dashboard\main.py
```

The dashboard will be available at:

- http://127.0.0.1:8000

The Flask monitoring server will run on:

- http://127.0.0.1:5000

## Usage notes

- Open the app and configure the camera source, target object, location, and contact details.
- If enable local storage, it will sent the image (consume storage in email)
- If enable cloud storage, it will sent the URL of the image (less stoarge consume in email)
- Enable alerts if you want snapshots and email notifications.
- For mobile viewing, choose the mobile source and scan the generated QR code.
- If ngrok is enabled and configured, the app will expose a public URL for remote viewing.

## Notes
- This overall model Acuracy is only 49%. knife  detect rate is hight trhen other classes
- The detection model is expected at weights/best.pt.
- If the model file is missing, detection will not run until the correct weights are placed in the folder.
- The alert dashboard depends on the local Flask app and the desktop client being available for the full monitoring workflow.

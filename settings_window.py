from PyQt6.QtWidgets import QMainWindow, QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.uic import loadUi
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from detection_window import DetectionWindow
from web_server import AppState
import requests
import socket
import threading

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class QrCodeDialog(QDialog):
    def __init__(self, url, qr_data=None, parent=None):
        super(QrCodeDialog, self).__init__(parent)
        self.setWindowTitle("Mobile Remote Access")
        self.setFixedSize(320, 370)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)

        info_label = QLabel(
            "<b>Scan QR code on your phone!</b><br>"
            "Open the link to view the live monitoring dashboard remotely."
        )
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("font-size: 11px; color: #374151; margin-bottom: 4px;")
        layout.addWidget(info_label)

        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if qr_data:
            pixmap = QPixmap()
            pixmap.loadFromData(qr_data)
            qr_label.setPixmap(pixmap)
            qr_label.setStyleSheet("border: 1px solid #e5e7eb; padding: 6px; background: white; border-radius: 8px;")
        else:
            qr_label.setText("[QR Code Unavailable - check internet connection]")
            qr_label.setStyleSheet("border: 1px solid #fca5a5; color: #ef4444; padding: 20px; font-weight: bold;")
        layout.addWidget(qr_label)

        link_label = QLabel(f'<a href="{url}" style="color: #2563eb; text-decoration: none;">{url}</a>')
        link_label.setOpenExternalLinks(True)
        link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link_label.setStyleSheet("font-size: 11px; font-weight: bold; margin-top: 4px;")
        link_label.setWordWrap(True)
        layout.addWidget(link_label)

        close_button = QPushButton("Got It!")
        close_button.setStyleSheet(
            "background-color: #1f2937; color: white; border: none; padding: 8px; "
            "border-radius: 6px; font-weight: bold; margin-top: 8px;"
        )
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)


class SettingsWindow(QMainWindow):
    def __init__(self):
        super(SettingsWindow, self).__init__()
        loadUi("UI/settings_window.ui", self)

        self.detection_window = DetectionWindow()

        # Wire up source dropdown to toggle RTSP field visibility
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)

        self.monitoring_button.clicked.connect(self.go_to_detection)

        # Wire up alert toggle button
        self.alert_toggle_btn.clicked.connect(self.on_alert_toggled)
        self.update_alert_btn_style(False)
        AppState.alerts_enabled = False

        # Storage combo: hidden by default, shown when alerts are ON
        self.label_storage.setVisible(False)
        self.storage_combo.setVisible(False)

        # Set default target class
        AppState.target_class = "all"

        # Apply layout dynamics for initial source setting
        self.on_source_changed(0)

    def update_alert_btn_style(self, checked):
        if checked:
            self.alert_toggle_btn.setText("Alerts: ON")
            self.alert_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #16a34a; /* Green */
                    color: white;
                    border: 1px solid #22c55e;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #15803d;
                }
            """)
        else:
            self.alert_toggle_btn.setText("Alerts: OFF")
            self.alert_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc2626; /* Red */
                    color: white;
                    border: 1px solid #ef4444;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #b91c1c;
                }
            """)

    def on_alert_toggled(self, checked):
        AppState.alerts_enabled = checked
        self.update_alert_btn_style(checked)
        # Show/hide storage mode picker
        self.label_storage.setVisible(checked)
        self.storage_combo.setVisible(checked)
        self._reposition_controls()

    def on_source_changed(self, index):
        source = self.source_combo.currentText()
        show_rtsp = (source == "CCTV (RTSP)")
        self.label_rtsp.setVisible(show_rtsp)
        self.rtsp_input.setVisible(show_rtsp)
        self._reposition_controls()

    def _reposition_controls(self):
        """Reposition all controls dynamically based on visible sections."""
        x = 15
        y = 105  # Start after alert toggle button (y=65 + h=30 + spacing)

        # Storage mode (only when alerts ON)
        show_storage = self.label_storage.isVisible()
        if show_storage:
            self.label_storage.move(x, y)
            y += 20
            self.storage_combo.move(x, y)
            y += 35
        
        # Object to Detect
        self.label_target.move(x, y)
        y += 20
        self.target_combo.move(x, y)
        y += 35

        # Camera Source
        self.label_source.move(x, y)
        y += 20
        self.source_combo.move(x, y)
        y += 35

        # RTSP (only when CCTV selected)
        show_rtsp = self.label_rtsp.isVisible()
        if show_rtsp:
            self.label_rtsp.move(x, y)
            y += 20
            self.rtsp_input.move(x, y)
            y += 30

        # Location
        self.label_location.move(x, y)
        y += 20
        self.location_input.move(x, y)
        y += 30

        # Contact
        self.label_contact.move(x, y)
        y += 20
        self.contact_input.move(x, y)
        y += 30

        # QR Code Mode
        self.label_qr_mode.move(x, y)
        y += 20
        self.qr_mode_combo.move(x, y)
        y += 35

        # Start Monitoring button
        self.monitoring_button.move(x, y)
        y += 45

        self.setFixedHeight(y)

    def displayInfo(self):
        self.show()

    def fetch_qr_and_show_dialog(self, url):
        import io
        import qrcode
        qr_data = None
        try:
            img = qrcode.make(url)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            qr_data = buf.getvalue()
        except Exception as e:
            print(f"Error generating QR code: {e}")

        dialog = QrCodeDialog(url, qr_data, self)
        dialog.exec()

    def go_to_detection(self):
        if self.detection_window.isVisible():
            print("Detection window is already open!")
            return

        source = self.source_combo.currentText()
        location_text = self.location_input.text().strip() or "Main Entrance"
        contact_text = self.contact_input.text().strip() or "Not Configured"
        rtsp_url = self.rtsp_input.text().strip() if source == "CCTV (RTSP)" else ""

        # Update shared AppState
        AppState.location = location_text
        AppState.contact = contact_text
        AppState.target_class = self.target_combo.currentText().strip().lower()
        AppState.running = True
        AppState.source_type = source.lower().replace(" (rtsp)", "").replace(" ", "_")
        # Normalize: "webcam", "cctv", "mobile"
        if "cctv" in AppState.source_type:
            AppState.source_type = "cctv"
        elif "mobile" in AppState.source_type:
            AppState.source_type = "mobile"
        else:
            AppState.source_type = "webcam"

        # Push selected storage mode to dashboard API (in background)
        if AppState.alerts_enabled:
            selected_storage = self.storage_combo.currentText()
            storage_mode = "cloud" if "Cloud" in selected_storage else "local"
            def _push_storage_mode():
                try:
                    import requests as req
                    req.post(
                        "http://localhost:8000/api/config",
                        json={"storage_mode": storage_mode},
                        timeout=3
                    )
                    print(f"Storage mode set to: {storage_mode}")
                except Exception as e:
                    print(f"Could not update storage mode on dashboard: {e}")
            threading.Thread(target=_push_storage_mode, daemon=True).start()

        # Pick the best remote URL (ngrok HTTPS preferred, then local IP)
        ngrok_url = getattr(AppState, 'ngrok_url', None)
        if ngrok_url:
            # Always prefer https for getUserMedia camera API on phone
            base_url = ngrok_url.replace("http://", "https://") if ngrok_url.startswith("http://") else ngrok_url
        else:
            local_ip = get_local_ip()
            base_url = f"http://{local_ip}:5000"

        # Create a fresh DetectionWindow for this session
        self.detection_window = DetectionWindow()
        self.detection_window.create_detection_instance(
            source_type=AppState.source_type,
            rtsp_url=rtsp_url
        )
        self.detection_window.start_detection(base_url=base_url)

        # Check QR mode dropdown
        qr_mode = self.qr_mode_combo.currentText()
        
        # Only show QR popup if "QR" is selected
        if qr_mode == "QR":
            # For Mobile mode, only show QR code dialog (no dashboard QR)
            if AppState.source_type == "mobile":
                camera_url = base_url + "?mode=camera"
                threading.Thread(target=self.fetch_qr_and_show_dialog, args=(camera_url,), daemon=True).start()
            else:
                # For Webcam/CCTV: show dashboard URL as QR
                threading.Thread(target=self.fetch_qr_and_show_dialog, args=(base_url,), daemon=True).start()

    def closeEvent(self, event):
        AppState.running = False
        if self.detection_window.isVisible():
            if self.detection_window.detection:
                self.detection_window.detection.running = False
            self.detection_window.close()
        event.accept()

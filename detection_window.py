from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.uic import loadUi
from PyQt6.QtCore import pyqtSlot, Qt, QEvent, QUrl
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from detection import Detection
from web_server import AppState
import requests
import threading
import os


def _fetch_qr_pixmap(url):
    """Fetch a QR code image as QPixmap for the given URL."""
    try:
        api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={url}"
        response = requests.get(api_url, timeout=6)
        if response.status_code == 200:
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            return pixmap
    except Exception as e:
        print(f"Error fetching QR code: {e}")
    return None


class DetectionWindow(QMainWindow):
    def __init__(self):
        super(DetectionWindow, self).__init__()
        loadUi('UI/detection_window.ui', self)

        # Enable Minimize and Maximize
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        self.setMaximumSize(16777215, 16777215)

        # Responsive layout
        main_layout = QVBoxLayout(self.centralwidget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        self.label_detection.setMinimumSize(400, 300)
        self.label_detection.setMaximumSize(16777215, 16777215)
        self.label_detection.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_detection.setStyleSheet("background-color: #060a12; border-radius: 8px;")
        main_layout.addWidget(self.label_detection, stretch=1)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.stop_detection_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.label_detection.installEventFilter(self)
        self.stop_detection_button.clicked.connect(self.close)
        self.detection = None
        self._source_type = "webcam"
        self._base_url = None
        self._qr_shown = False

        # Alert sound player
        self._audio_output = QAudioOutput()
        self._audio_output.setVolume(1.0)
        self._alert_player = QMediaPlayer()
        self._alert_player.setAudioOutput(self._audio_output)
        alert_path = os.path.join(os.path.dirname(__file__), 'alert_img', 'alert.mp3')
        self._alert_player.setSource(QUrl.fromLocalFile(alert_path))

    def create_detection_instance(self, source_type="webcam", rtsp_url=""):
        self._source_type = source_type
        if self.detection is None or not self.detection.running:
            self.detection = Detection()
            self.detection.source_type = source_type
            self.detection.rtsp_url = rtsp_url

    @pyqtSlot(QImage)
    def setImage(self, image):
        # If mobile mode, remove any QR code overlay once frames start arriving
        if self._source_type == "mobile" and not self._qr_shown:
            self._qr_shown = True

        pixmap = QPixmap.fromImage(image)
        scaled_pixmap = pixmap.scaled(
            self.label_detection.width(),
            self.label_detection.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        self.label_detection.setPixmap(scaled_pixmap)

    @pyqtSlot()
    def _on_alert(self):
        """Play alert sound when a high-confidence detection occurs."""
        self._alert_player.stop()
        self._alert_player.setPosition(0)
        self._alert_player.play()

    def _show_mobile_waiting_screen(self, camera_url):
        """Show the QR code and waiting message in the video label."""
        qr_pixmap = _fetch_qr_pixmap(camera_url)
        if qr_pixmap:
            # Create composite image: dark background + QR code centered
            from PyQt6.QtGui import QPainter, QColor, QFont
            from PyQt6.QtCore import QRect
            canvas_w, canvas_h = 640, 480
            canvas = QPixmap(canvas_w, canvas_h)
            canvas.fill(QColor(6, 10, 18))  # dark background

            painter = QPainter(canvas)
            # QR code centered
            qr_x = (canvas_w - qr_pixmap.width()) // 2
            qr_y = (canvas_h - qr_pixmap.height()) // 2 - 30
            painter.drawPixmap(qr_x, qr_y, qr_pixmap)

            # Instructions text
            painter.setPen(QColor(243, 244, 246))
            font = QFont("Arial", 11, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(QRect(0, qr_y + qr_pixmap.height() + 12, canvas_w, 28),
                             Qt.AlignmentFlag.AlignCenter, "Scan QR code to stream from your phone")

            painter.setPen(QColor(156, 163, 175))
            font2 = QFont("Arial", 9)
            painter.setFont(font2)
            painter.drawText(QRect(0, qr_y + qr_pixmap.height() + 38, canvas_w, 24),
                             Qt.AlignmentFlag.AlignCenter, "Waiting for mobile connection...")
            painter.end()

            self.label_detection.setPixmap(canvas.scaled(
                self.label_detection.width(),
                self.label_detection.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.label_detection.setText(
                "📱 Scan the QR code popup to stream from your phone.\n\nWaiting for mobile connection..."
            )
            self.label_detection.setStyleSheet(
                "background-color: #060a12; color: #9ca3af; font-size: 14px;"
            )

    def start_detection(self, base_url=None):
        if self.detection is None:
            self.create_detection_instance()
        self._base_url = base_url

        self.detection.changePixmap.connect(self.setImage)
        self.detection.playAlert.connect(self._on_alert)
        self.showMaximized()

        if self._source_type == "mobile":
            # Compute the camera URL
            camera_url = (base_url + "?mode=camera") if base_url else "http://localhost:5000?mode=camera"
            # Show waiting screen in a background thread (QR fetching might take a second)
            threading.Thread(target=self._show_mobile_waiting_screen, args=(camera_url,), daemon=True).start()

        self.detection.start()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def mouseDoubleClickEvent(self, event):
        self.toggle_fullscreen()

    def eventFilter(self, source, event):
        if source is self.label_detection and event.type() == QEvent.Type.MouseButtonDblClick:
            self.toggle_fullscreen()
            return True
        return super(DetectionWindow, self).eventFilter(source, event)

    def closeEvent(self, event):
        AppState.running = False
        if self.detection is not None:
            self.detection.running = False
            self.detection.wait()
        event.accept()

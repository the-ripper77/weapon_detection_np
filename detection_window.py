from PyQt5.QtWidgets import QMainWindow
from PyQt5.uic import loadUi
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from detection import Detection

class DetectionWindow(QMainWindow):
    def __init__(self):
        super(DetectionWindow, self).__init__()
        loadUi('UI/detection_window.ui', self)
        self.stop_detection_button.clicked.connect(self.close)
        self.detection = None

    def create_detection_instance(self):
        if self.detection is None or not self.detection.running:
            self.detection = Detection()

    @pyqtSlot(QImage)
    def setImage(self, image):
        self.label_detection.setPixmap(QPixmap.fromImage(image))

    def start_detection(self):
        if self.detection is None:
            self.create_detection_instance()
        self.detection.changePixmap.connect(self.setImage)
        self.detection.start()
        self.show()

    def closeEvent(self, event):
        if self.detection is not None:
            self.detection.running = False
            self.detection.wait()
        event.accept()

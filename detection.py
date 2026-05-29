from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QImage
import cv2

class Detection(QThread):
    changePixmap = pyqtSignal(QImage)

    def __init__(self):
        super(Detection, self).__init__()
        self.running = False

    def run(self):
        self.running = True
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Error: Could not open video capture device.")
            return

        while self.running:
            ret, frame = cap.read()
            if ret:
                height, width, channels = frame.shape
                rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                bytesPerLine = channels * width
                convertToQtFormat = QImage(rgbImage.data, width, height, bytesPerLine, QImage.Format_RGB888)
                p = convertToQtFormat.scaled(860, 680, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.changePixmap.emit(p)
            else:
                print("Failed to grab frame")

        cap.release()

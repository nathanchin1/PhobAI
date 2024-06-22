import sys
import numpy as np
import cv2
import mss
from PyQt5 import QtCore, QtGui, QtWidgets
from ultralytics import YOLO

# Initialize YOLO model (consider using a more accurate model if needed)
model = YOLO("yolov8n.pt")  # pretrained model

# Define screen capture parameters
mon = {"top": 0, "left": 0, "width": 1512, "height": 982}  # Adjust these values based on your screen resolution

# Initialize mss
sct = mss.mss()

class TrackingBox(QtWidgets.QLabel):
    def __init__(self, score, classification, box, parent=None):
        super().__init__(parent)
        x, y, width, height = box
        self.setGeometry(x, y, width, height)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setStyleSheet("border: 2px solid red;")

        label = QtWidgets.QLabel(f"{int(score * 100)}% {classification}", self)
        label.setStyleSheet("color: red; background-color: white;")
        label.move(5, 5)

        self.show()

class MainApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(0, 0, mon["width"], mon["height"])
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # Timer for updating screen capture
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.updateScreen)
        self.timer.start(58)  # Update every 58 ms

        # List to keep track of tracking boxes
        self.tracking_boxes = []

    def updateScreen(self):
        # Capture screen image
        im = np.array(sct.grab(mon))

        # Ensure image has 3 channels (RGB)
        if im.shape[2] == 4:
            im = cv2.cvtColor(im, cv2.COLOR_RGBA2RGB)

        results = model.predict(im, show=False)
        boxes = results[0].boxes.xyxy.cpu().numpy()
        scores = results[0].boxes.conf.cpu().numpy()
        clss = results[0].boxes.cls.cpu().numpy()

        # Remove old widgets
        for box in self.tracking_boxes:
            box.deleteLater()
        self.tracking_boxes = []

        if boxes is not None:
            for box, score, cls in zip(boxes, scores, clss):
                # Filter out low-confidence detections
                if score < 0.5:
                    continue

                # Calculate coordinates for bounding box
                x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
                width, height = x2 - x1, y2 - y1
                
                # Scale coordinates to match the display
                x1 = int(x1 * mon["width"] / im.shape[1])
                y1 = int(y1 * mon["height"] / im.shape[0])
                width = int(width * mon["width"] / im.shape[1])
                height = int(height * mon["height"] / im.shape[0])

                classification = model.names[int(cls)]

                # Create and show tracking box
                tracking_box = TrackingBox(score, classification, (x1, y1, width, height), self)
                self.tracking_boxes.append(tracking_box)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_app = MainApp()
    main_app.show()
    sys.exit(app.exec_())

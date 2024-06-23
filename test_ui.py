import sys
import numpy as np
import cv2
import mss
from PyQt5 import QtCore, QtGui, QtWidgets
from ultralytics import YOLO
import boto3
import json
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# Load environment variables from .env file
load_dotenv()

# Initialize the Bedrock runtime client with credentials from the environment
bedrock_runtime = boto3.client(
    'bedrock-runtime',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name='us-east-1'
)

# Initialize YOLO model (consider using a more accurate model if needed)
model = YOLO("yolov8m.pt")  # pretrained model

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

class TrackingApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(0, 0, mon["width"], mon["height"])
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # Timer for updating screen capture
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.updateScreen)

        # List to keep track of tracking boxes
        self.tracking_boxes = []

    def start(self):
        self.timer.start(50)  # Update every 50 ms

    def stop(self):
        self.timer.stop()
        for box in self.tracking_boxes:
            box.deleteLater()
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

class HoverButton(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)

    def enterEvent(self, event):
        self.setStyleSheet("background-color: #FFDDC1; color: #457B9D; border-radius: 10px;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("background-color: #457B9D; color: #FFDDC1; border-radius: 10px;")
        super().leaveEvent(event)

class MainApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Phob.ai")
        self.setGeometry(100, 100, 600, 400)
        self.setStyleSheet("background-color: #F1FAEE;")

        self.title_label = QtWidgets.QLabel("Phob.ai", self)
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.title_label.setGeometry(50, 30, 500, 100)
        font = QtGui.QFont("Arial", 16, QtGui.QFont.Bold)
        font.setPointSize(70)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: #A8DADC;")
        
        font2 = QtGui.QFont("Arial", 16, QtGui.QFont.Bold)

        self.start_button = HoverButton("Start", self)
        self.start_button.setGeometry(250, 160, 100, 40)
        self.start_button.clicked.connect(self.start_tracking)
        self.start_button.setStyleSheet("background-color: #457B9D; color: #FFDDC1; border-radius: 10px;")
        self.start_button.setFont(font2)

        self.stop_button = HoverButton("Stop", self)
        self.stop_button.setGeometry(250, 160, 100, 40)
        self.stop_button.clicked.connect(self.stop_tracking)
        self.stop_button.hide()
        self.stop_button.setStyleSheet("background-color: #457B9D; color: #FFDDC1; border-radius: 10px;")
        self.stop_button.setFont(font2)

        self.edit_button = HoverButton("Edit", self)
        self.edit_button.setGeometry(250, 220, 100, 40)
        self.edit_button.clicked.connect(self.show_edit_view)
        self.edit_button.setStyleSheet("background-color: #457B9D; color: #FFDDC1; border-radius: 10px;")
        self.edit_button.setFont(font2)

        self.textbox = QtWidgets.QLineEdit(self)
        self.textbox.setGeometry(200, 100, 200, 30)
        self.textbox.hide()
        self.textbox.setStyleSheet("background-color: #E9C46A; color: #F1FAEE; border-radius: 10px;")
        self.textbox.setFont(font2)

        self.save_button = HoverButton("Save", self)
        self.save_button.setGeometry(250, 160, 100, 40)
        self.save_button.clicked.connect(self.process_text)
        self.save_button.hide()
        self.save_button.setStyleSheet("background-color: #457B9D; color: #FFDDC1; border-radius: 10px;")
        self.save_button.setFont(font2)

        self.back_button = HoverButton("Back", self)
        self.back_button.setGeometry(250, 220, 100, 40)
        self.back_button.clicked.connect(self.show_main_view)
        self.back_button.hide()
        self.back_button.setStyleSheet("background-color: #457B9D; color: #FFDDC1; border-radius: 10px;")
        self.back_button.setFont(font2)

    def start_tracking(self):
        self.tracking_app = TrackingApp()
        self.tracking_app.show()
        self.tracking_app.start()
        self.start_button.hide()
        self.stop_button.show()

    def stop_tracking(self):
        self.tracking_app.stop()
        self.tracking_app.close()
        self.stop_button.hide()
        self.start_button.show()

    def show_edit_view(self):
        self.title_label.hide()
        self.start_button.hide()
        self.stop_button.hide()
        self.edit_button.hide()
        self.textbox.show()
        self.save_button.show()
        self.back_button.show()

    def show_main_view(self):
        self.title_label.show()
        self.start_button.show()
        self.stop_button.hide()
        self.edit_button.show()
        self.textbox.hide()
        self.save_button.hide()
        self.back_button.hide()

    def process_text(self):
        input_text = self.textbox.text()
        body = json.dumps({
            "max_tokens": 256,
            "messages": [{"role": "user", "content": f'''For the following word, if the word is deemed too broad, reply with a list of objects that correspond to this term in the form of a python list. If the word is specific enough, reply with just that word in the form of a python list. Only have singular words, no plural. The word is "{input_text}".'''}],
            "anthropic_version": "bedrock-2023-05-31"
        })

        try:
            response = bedrock_runtime.invoke_model(body=body, modelId="anthropic.claude-3-5-sonnet-20240620-v1:0")
            response_body = json.loads(response.get("body").read())
            print(response_body["content"][0]["text"])
        except ClientError as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_app = MainApp()
    main_app.show()
    sys.exit(app.exec_())


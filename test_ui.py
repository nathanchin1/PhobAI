import sys, cv2, mss, boto3, json, os
import numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from ultralytics import YOLO
from pynput import mouse as pynput_mouse
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

bedrock_runtime = boto3.client(
    'bedrock-runtime',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name='us-east-1'
)

# TODO: Update to pretrained
model = YOLO("phobiamed10.pt")  

mon = {"top": 0, "left": 0, "width": 1920, "height": 1080}  

sct = mss.mss()

class TrackingBox(QtWidgets.QLabel):  
    def __init__(self, score, classification, box, parent=None):
        super().__init__(parent)
        x, y, width, height = box 
        self.setGeometry(x, y, width, height) 
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint) 
        self.setStyleSheet("background-color: rgba(173, 216, 230, 255);") # TODO blur section

        # Create conf and cls label for widget overlay
        # label = QtWidgets.QLabel(f"{int(score * 100)}% {classification}", self) 
        # label.setStyleSheet("color: red; background-color: rgba(255, 255, 255, 0);") 
        # label.move(5, 5) 

        self.show()

class MainApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(0, 0, mon["width"], mon["height"]) # Set window to cover entire screen
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.WA_TranslucentBackground) 
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # Timer for updating screen capture
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.updateScreen)
        self.timer.start(100)  # speed depends on computer gpu

        # Store tracking widgets
        self.tracking_boxes = []

        # pynput mouse listener for click & scroll
        self.mouse_click_listener = pynput_mouse.Listener(on_click=self.on_mouse_click, on_scroll=self.on_mouse_scroll)
        self.mouse_click_listener.start()
        
        
        
        

    def on_mouse_click(self, x, y, button, pressed):
        if pressed and button == pynput_mouse.Button.left:
            if self.tracking_boxes:
                for box in self.tracking_boxes:
                    box.deleteLater()
                self.tracking_boxes = []

    def on_mouse_scroll(self, x, y, dx, dy):
        if dy != 0:
            if self.tracking_boxes:
                for box in self.tracking_boxes:
                    box.deleteLater()
                self.tracking_boxes = []

    def updateScreen(self):
        # Capture current screen
        im = np.array(sct.grab(mon))

        # Ensure image has 3 channels (RGB)
        if im.shape[2] == 4:
            im = cv2.cvtColor(im, cv2.COLOR_RGBA2RGB)

        # YOLO detection box data
        results = model.predict(im, show=False)
        boxes = results[0].boxes.xyxy.cpu().numpy()
        scores = results[0].boxes.conf.cpu().numpy()
        clss = results[0].boxes.cls.cpu().numpy()

        # Remove old widgets if not toggled off by click or scroll
        if not self.tracking_boxes:
            for box in self.tracking_boxes:
                box.deleteLater()
            self.tracking_boxes = []

        if boxes is not None:
            for box, score, cls in zip(boxes, scores, clss):
                # Filter out low conf scores
                if score < 0.45:
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

class StartWindow(QtWidgets.QWidget):
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

        self.saved_label = QtWidgets.QLabel("Saved!", self)
        self.saved_label.setAlignment(QtCore.Qt.AlignCenter)
        self.saved_label.setGeometry(200, 60, 200, 30)
        self.saved_label.setStyleSheet("color: green; background-color: rgba(255, 255, 255, 0);")
        self.saved_label.setFont(font2)
        self.saved_label.hide()

    def start_tracking(self):
        self.main_app = MainApp()
        self.main_app.show()
        self.start_button.hide()
        self.stop_button.show()

    def stop_tracking(self):
        if hasattr(self, 'main_app') and self.main_app.isVisible():
            self.main_app.timer.stop()  # Stop the timer to stop the model
            self.main_app.close()
        self.start_button.show()
        self.stop_button.hide()

    def show_edit_view(self):
        self.title_label.hide()
        self.start_button.hide()
        self.stop_button.hide()
        self.edit_button.hide()
        self.textbox.show()
        self.save_button.show()
        self.back_button.show()

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
            self.saved_label.show()  # Show the "Saved!" label
        except ClientError as e:
            print(f"An error occurred: {e}")

    def show_main_view(self):
        self.textbox.hide()
        self.save_button.hide()
        self.back_button.hide()
        self.saved_label.hide()
        self.title_label.show()
        self.start_button.show()
        self.stop_button.hide()
        self.edit_button.show()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    start_window = StartWindow()
    start_window.show()
    sys.exit(app.exec_())

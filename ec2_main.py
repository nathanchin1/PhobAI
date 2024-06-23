# runs on ec2 instance to train yolov8 model from s3 data
object_name = 'Users/userid1/stablediffusion/data.zip'
s3_client.download_file(bucket_name, object_name, 'data.zip')

with zipfile.ZipFile('data.zip', 'r') as zip_ref:
    zip_ref.extractall('./data/')

# current directory:
#
# ├── data
# │   ├── test
# │   │   ├── images
# │   │   └── labels
# │   ├── train
# │   │   ├── images
# │   │   └── labels
# │   ├── valid
# │   │   ├── images
# │   │   └── labels
# │   ├── data.yaml
# │   └── README.data

#train yolo model
yolo_cmd = ("yolo task=detect mode=train model=yolov8n.pt data=data/data.yaml epochs=1 imgsz=100 plots=True")
os.system(yolo_cmd)
model = 'runs/detect/train/weights/best.pt'
s3_client.upload_file(model, bucket_name, 'Users/userid1/yolov8s_best.pt')
rm_cmd = ("rm -r runs data data.zip")
os.system(rm_cmd)

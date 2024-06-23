import boto3, json, os, base64, io, time, random
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from PIL import Image

load_dotenv()

bedrock_runtime = boto3.client(
    'bedrock-runtime',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name='us-east-1' 
)

user_input = str(input("Write down what you do not want to see: "))

body = json.dumps({
    "max_tokens": 256,
    "messages": [{"role": "user", "content": f'''For the following word, if the word is deemed too broad, reply with a list of objects that correspond to this term in the form of a python list. If the word is specific enough, reply with just that word in the form of a python list. Only have singular words, no plural. The word is "{user_input}".'''}],
    "anthropic_version": "bedrock-2023-05-31"
})

try:
    response = bedrock_runtime.invoke_model(body=body, modelId="anthropic.claude-3-5-sonnet-20240620-v1:0")
    response_body = json.loads(response.get("body").read())
    response = json.loads(response_body["content"][0]["text"])
    print(response)
except ClientError as e:
    print(f"An error occurred: {e}")

output_directory = "test_images"
os.makedirs(output_directory, exist_ok=True)

def resize_image(input_image_path, output_image_path, size=(1024, 1024)):
    with Image.open(input_image_path) as image:
        resized_image = image.resize(size)
        resized_image.save(output_image_path)
        print(f"{output_image_path} is being used.")

for obj in response:
    for i in range(10):  
        # TODO: To be replaced with S3 bucket with webscraped results
        source_directory = "source_images"
        source_images = [os.path.join(source_directory, file) for file in os.listdir(source_directory) if file.endswith(('png', 'jpg', 'jpeg'))]
        random_image = random.choice(source_images)

        resize_image(random_image, random_image)

        with open(random_image, "rb") as image_file:
            init_image_base64 = base64.b64encode(image_file.read()).decode('utf8')

        body = json.dumps({
            "text_prompts": [{
                "text": f"{obj} by itself on an empty white background. Only one object in the picture.",
                "weight": 10
                }],
            "init_image": init_image_base64,
            "image_strength": 0.3,
            "cfg_scale": 13,
            "seed": random.randint(10, 200) + i,  
            "steps": 45
        })

        modelId = 'stability.stable-diffusion-xl-v1'
        accept = "application/json"
        contentType = "application/json"

        try:
            response = bedrock_runtime.invoke_model(
                body=body, modelId=modelId, accept=accept, contentType=contentType
            )

            response_body = json.loads(response.get("body").read())

            base_64_img_str = response_body.get("artifacts")[0].get("base64")

            image = Image.open(io.BytesIO(base64.decodebytes(bytes(base_64_img_str, "utf-8"))))

            file_name = f"{obj.replace(' ', '_')}_{i}_{int(time.time())}.png"
            file_path = os.path.join(output_directory, file_name)

            image.save(file_path)
            print(f"Image saved to {file_path}")
        except ClientError as e:
            print(f"An error occurred: {e.response['Error']['Message']}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
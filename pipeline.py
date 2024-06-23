import boto3
import json
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError
import base64
import io
from PIL import Image
import time

# Load environment variables from .env file
load_dotenv()

# Initialize the Bedrock runtime client with credentials from the environment
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

# Ensure the 'test_images' directory exists
output_directory = "test_images"
os.makedirs(output_directory, exist_ok=True)

for obj in response:
    for i in range(10):  # Generate 10 images per object
        body = json.dumps({
            "text_prompts": [{
                "text": f"{obj} by itself on an empty white background. Only one object in the picture.",
                "weight": 10
                }],
            "cfg_scale": 13,
            "seed": 20 + i,  # Change the seed for each image to get different variations
            "steps": 45
        })

        # Model details
        modelId = "stability.stable-diffusion-xl-v1"
        accept = "application/json"
        contentType = "application/json"

        try:
            # Invoke the model
            response = bedrock_runtime.invoke_model(
                body=body, modelId=modelId, accept=accept, contentType=contentType
            )

            # Parse the response body
            response_body = json.loads(response.get("body").read())

            # Get the base64 encoded image string
            base_64_img_str = response_body.get("artifacts")[0].get("base64")

            # Decode the base64 image string and open it as an image
            image = Image.open(io.BytesIO(base64.decodebytes(bytes(base_64_img_str, "utf-8"))))

            # Generate a unique file name
            file_name = f"{obj.replace(' ', '_')}_{i}_{int(time.time())}.png"
            file_path = os.path.join(output_directory, file_name)

            # Save the image to the specified file path
            image.save(file_path)
            print(f"Image saved to {file_path}")
        except ClientError as e:
            print(f"An error occurred: {e.response['Error']['Message']}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


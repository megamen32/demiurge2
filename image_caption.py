import os

import boto3
import openai
from PIL import Image

from gpt_image import predict

client = boto3.client('rekognition',region_name='eu-paris')
from google.cloud import vision
import os

def image_caption_generator(image_path):
    # Open the original image
    # Use Google Cloud Vision on the image

    image=Image.open(image_path)
    labels_str=predict(image)
    return labels_str


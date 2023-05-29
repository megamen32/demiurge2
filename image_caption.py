import os

import boto3
import openai
from PIL import Image

client = boto3.client('rekognition',region_name='eu-paris')


def image_caption_generator(image_path):
    # create a tmp folder in order to save the resized input image
    if not os.path.exists('tmp'):
        os.makedirs('tmp')

    # Open the original image
    img = Image.open(image_path)

    # Set the desired size for the resized image
    new_size = (100, 100)

    # Resize the image
    resized_img = img.resize(new_size)

    # Save the resized image
    resized_img.save('tmp/tmp.jpg')

    with open('tmp/tmp.jpg', 'rb') as image:
        response = client.detect_labels(Image={'Bytes': image.read()})

    image_labels = []
    for label in response['Labels']:
        if label['Confidence'] > 70:
            image_labels.append(label['Name'].lower())

    # Generate a prompt by concatenating the image labels
    prompt = 'Generate an image caption for the following image labels: ' + ', '.join(image_labels)

    # Use the OpenAI API to generate image captions
    response = openai.Completion.create(
        model='text-davinci-003',
        prompt=prompt,
        temperature=0.5,
        max_tokens=50
    )

    # Extract the generated image captions from the API response
    generated_captions = response['choices'][0]['text']

    output = 'Generated Image Captions:\n' + generated_captions

    return output
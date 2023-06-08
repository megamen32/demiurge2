
from PIL import Image

from gpt_image import predict


def image_caption_generator(image_path):
    # Open the original image
    # Use Google Cloud Vision on the image

    image=Image.open(image_path)
    labels_str=predict(image)
    return labels_str


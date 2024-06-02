from rembg import remove
from PIL import Image
from dotenv import load_dotenv

from settings import Settings

import io

load_dotenv()

settings = Settings()


def remove_background(image_data):
    # Load image from bytes
    input_image = Image.open(io.BytesIO(image_data))

    # Remove background
    output_image = remove(input_image)

    # Save to bytes
    img_byte_arr = io.BytesIO()
    output_image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    return img_byte_arr
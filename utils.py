from rembg import remove
from PIL import Image
from dotenv import load_dotenv

from settings import Settings

import io
from io import BytesIO

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


def move_image_to_bottom(image_data):
    # Open the image
    image = Image.open(BytesIO(image_data))
    width, height = image.size

    # Create a new image with the same dimensions
    new_image = Image.new('RGBA', (width, height))

    # Start from the bottom of the new image
    current_height = height - 1

    # Iterate over the pixels of the original image from bottom to top
    for y in reversed(range(height)):
        row_has_non_transparent_pixel = False
        for x in range(width):
            pixel = image.getpixel((x, y))

            # If the pixel is not transparent, copy it to the new image
            if pixel[3] > 0:  # The fourth element is the alpha (transparency)
                if current_height >= 0:  # Ensure we're not going outside the image boundaries
                    new_image.putpixel((x, current_height), pixel)
                    row_has_non_transparent_pixel = True

        # Move up one row in the new image
        current_height -= 1

        # If the row has no non-transparent pixels, break the loop
        if not row_has_non_transparent_pixel:
            current_height += 1  # Restore the current height to the last non-transparent row
            break

    # Calculate the crop height correctly
    crop_height = max(0, current_height)

    # Crop the new image to remove the transparent space at the bottom
    new_image = new_image.crop((0, crop_height, width, height))

    # Save the new image to a BytesIO object
    output = BytesIO()
    new_image.save(output, format='PNG')
    output.seek(0)
    return output.read()
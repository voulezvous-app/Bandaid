import json
from datetime import datetime
from io import BytesIO

import PIL
import blurhash
import cv2
import numpy as np
import requests
from PIL import Image
from devtools import debug
from tqdm import tqdm

from firebase_setup import db, bucket
from openai_setup import client, askOpenAI

import click

from utils import remove_background, move_image_to_bottom

commands = []


def command(func):
    commands.append(func)
    return func


# Start of the patches
@command
def fix_cocktail_ingredients_liquor_to_liqueur():
    cocktails_ref = db.collection('cocktails')

    docs = list(cocktails_ref.stream())
    print('number of docs:', len(docs))
    cocktails_updated = 0
    ingredients_updated = 0
    # for doc in docs:
    for doc in docs:
        cocktail_data = doc.to_dict()
        # Check if there's a 'ingredients' field
        if 'ingredients' in cocktail_data:
            for ingredient in cocktail_data['ingredients']:
                # Check if the ingredient is a liquor
                if 'isLiquor' in ingredient:
                    # Change 'isLiquor' to 'isLiqueur'
                    ingredient['isLiqueur'] = ingredient.pop('isLiquor')
                    ingredients_updated += 1

                # Change 'liquorType' to 'liqueurType'
                if 'liquorType' in ingredient:
                    ingredient['liqueurType'] = ingredient.pop('liquorType')

                    ingredients_updated += 1

            # Update the document in Firestore
            cocktails_ref.document(doc.id).set(cocktail_data)
            cocktails_updated += 1

        # Update the document in Firestore
        cocktails_ref.document(doc.id).set(cocktail_data)

    print(f'Updated {ingredients_updated} ingredients in {cocktails_updated} cocktails')


@command
def reset_alcohol_counters():
    alcohols_ref = db.collection('Alcohols')

    docs = list(alcohols_ref.stream())
    alcohols_updated = 0
    print('number of alcohols:', len(docs))
    for doc in docs:
        alcohol_data = doc.to_dict()

        # Set 'clickCounter' to 0
        alcohol_data['clickCounter'] = 0
        alcohol_data['savedCounter'] = 0
        alcohol_data['clickCounterWeekly'] = 0

        # Update the document in Firestore
        alcohols_ref.document(doc.id).set(alcohol_data)
        alcohols_updated += 1

    print(f'Updated {alcohols_updated} alcohols')


@command
def change_alcohols_set_liqueur_with_openai():
    alcohols_ref = db.collection('Alcohols')

    docs = list(alcohols_ref.stream())
    alcohols_updated = 0
    set_false_counter = 0
    set_true_counter = 0
    print('number of alcohols:', len(docs))
    for doc in tqdm(docs, desc="Processing alcohols"):
        alcohol_data = doc.to_dict()

        # delete the isLiquor field
        if 'isLiquor' in alcohol_data:
            del alcohol_data['isLiquor']

        # ask openai whether the alcohol is a liqueur or not
        # if it is a liqueur then set isLiqueur to True
        # else set isLiqueur to False

        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Is this a liqueur? respond with only 'True' or 'False'"},
                {"role": "user", "content": alcohol_data['name']}
            ]
        )
        response_content = completion.choices[0].message.content
        if response_content.lower() == 'true':
            alcohol_data['isLiqueur'] = True
            set_true_counter += 1
        else:
            alcohol_data['isLiqueur'] = False
            set_false_counter += 1

        # Update the document in Firestore
        alcohols_ref.document(doc.id).set(alcohol_data)
        alcohols_updated += 1

        # Update the document in Firestore
        alcohols_ref.document(doc.id).set(alcohol_data)

    print(f'Updated {alcohols_updated} alcohol; set True: {set_true_counter}, set False: {set_false_counter}')


@command
def set_cocktails_to_tags():
    # get tags from gist
    try:
        tags_json = requests.get(
            'https://gist.githubusercontent.com/PrenSJ2/91acf1ae805de805bbaf521b62e7dfc7/raw/35a7d769f45ad263e2556d14881d656a08bb6e72/vv_tags')
        tags = tags_json.json()
    except Exception as e:
        print(e)
        return

    cocktails_ref = db.collection('cocktails')

    docs = list(cocktails_ref.stream())
    print('number of docs:', len(docs))
    cocktails_updated = 0
    for doc in tqdm(docs, desc="Processing cocktails"):
        cocktail_data = doc.to_dict()

        print(f'--- {cocktail_data["name"]} ---')
        # use openai to set tags for the cocktail
        for key, values in tags.items():
            system_prompt = f'Given the following cocktail and any additional research you can find out about the cocktail, what {key} would you give it from the following list: {values}, always return only one array of tags, with double quotes nothing else\n\n'
            user_prompt = f'{cocktail_data}'
            response = askOpenAI(system_prompt, user_prompt)
            # Check if response is not empty and is a valid JSON string
            try:
                cocktail_data[key] = json.loads(response)
                print(f'{key}: {cocktail_data[key]}')
            except json.JSONDecodeError:
                print(f'Invalid JSON response for {key}: {response}')

        # Update the document in Firestore
        cocktails_ref.document(doc.id).set(cocktail_data)
        cocktails_updated += 1

    print(f'Updated {cocktails_updated} cocktails')


@command
def delete_tags_from_cocktails():
    cocktails_ref = db.collection('cocktails')

    docs = list(cocktails_ref.stream())
    print('number of docs:', len(docs))
    cocktails_updated = 0
    # docs = docs[:3]
    for doc in tqdm(docs, desc="Processing cocktails"):
        cocktail_data = doc.to_dict()
        # Check if there's a 'tags' field delete it
        if 'tags' in cocktail_data:
            del cocktail_data['tags']

        # Update the document in Firestore
        cocktails_ref.document(doc.id).set(cocktail_data)
        cocktails_updated += 1

    print(f'Updated {cocktails_updated} cocktails')


@command
def minimize_alcohol_smell_and_taste_into_tags():
    alcohols_ref = db.collection('Alcohols')

    docs = list(alcohols_ref.stream())
    print('number of alcohols:', len(docs))
    alcohols_updated = 0
    for doc in tqdm(docs, desc="Processing alcohols"):
        alcohol_data = doc.to_dict()
        # use openai to set tags for the alcohol
        for key in ['smell', 'taste']:
            system_prompt = 'summarize the given sentence into an array of tags, the fewer the better, always return only one array of tags, with double quotes nothing else'
            user_prompt = f'{alcohol_data[key]}'
            response = askOpenAI(system_prompt, user_prompt)
            # Check if response is not empty and is a valid JSON string
            try:
                alcohol_data[f'{key}_tags'] = json.loads(response)
            except json.JSONDecodeError:
                print(f'Invalid JSON response for {alcohol_data["name"]} {key}: {response}')

        # Update the document in Firestore
        alcohols_ref.document(doc.id).set(alcohol_data)
        alcohols_updated += 1

    print(f'Updated {alcohols_updated} alcohols')


@command
def delete_misc_alcohols_fields():
    alcohols_ref = db.collection('Alcohols')

    docs = list(alcohols_ref.stream())
    print('number of alcohols:', len(docs))
    alcohols_deleted = 0
    for doc in tqdm(docs, desc="Processing alcohols"):
        alcohol_data = doc.to_dict()
        # Patch: delete every alcohol with a description 'This product stands out due to ...'
        if 'description' in alcohol_data and alcohol_data['description'] == 'This product stands out due to ...':
            alcohols_ref.document(doc.id).delete()
            alcohols_deleted += 1
            continue

    print(f'Deleted {alcohols_deleted} alcohols')


@command
def update_alcohols_countryemoji_from_country():
    alcohols_ref = db.collection('Alcohols')

    docs = list(alcohols_ref.stream())
    print('number of alcohols:', len(docs))
    alcohols_updated = 0
    for doc in tqdm(docs, desc="Processing alcohols"):
        alcohol_data = doc.to_dict()
        # Check if there's a 'country' field
        if 'country' in alcohol_data and alcohol_data['countryFlag'] == 'None':
            # Get the country emoji from the country
            system_prompt = 'given the country return only the country emoji'
            user_prompt = f'{alcohol_data["country"]}'
            alcohol_data['countryFlag'] = askOpenAI(system_prompt, user_prompt)

            # Update the document in Firestore
            alcohols_ref.document(doc.id).set(alcohol_data)
            alcohols_updated += 1

    print(f'Updated {alcohols_updated} alcohols')


@command
def update_england_emojis():
    alcohols_ref = db.collection('Alcohols')

    docs = list(alcohols_ref.stream())
    print('number of alcohols:', len(docs))
    alcohols_updated = 0
    for doc in tqdm(docs, desc="Processing alcohols"):
        alcohol_data = doc.to_dict()
        # Check if there's a 'country' field
        if 'country' in alcohol_data and alcohol_data['country'] == 'England':
            # Get the country emoji from the country
            alcohol_data['countryFlag'] = '🏴󠁧󠁢󠁥󠁮󠁧󠁿'

            # Update the document in Firestore
            alcohols_ref.document(doc.id).set(alcohol_data)
            alcohols_updated += 1

    print(f'Updated {alcohols_updated} England alcohols')


@command
def test_get_possible_cocktails():
    list_of_base_spirits = ['Vodka', 'Gin']

    # get all cocktails
    cocktails_ref = db.collection('cocktails')
    docs = list(cocktails_ref.stream())
    print('number of docs:', len(docs))

    possible_cocktail_refs = []

    for doc in tqdm(docs, desc="Processing cocktails"):
        cocktail_data = doc.to_dict()

        # Check if there's a 'ingredients' field
        if 'ingredients' in cocktail_data:
            for ingredient in cocktail_data['ingredients']:
                debug(ingredient['isLiqueur'])
                # Check if the ingredient is a liquor
                if ingredient['isLiqueur']:
                    # Check if the ingredient is a base spirit
                    if ingredient['liqueurType'] in list_of_base_spirits:
                        possible_cocktail_refs.append(cocktails_ref.document(doc.id))
                        break

                if ingredient['isSpirit']:
                    # Check if the ingredient is a base spirit
                    if ingredient['spiritType'] in list_of_base_spirits:
                        possible_cocktail_refs.append(cocktails_ref.document(doc.id))
                        break

    print(f'{len(possible_cocktail_refs)} possible cocktails')


@command
def remove_background_from_alc_images():
    blobs = list(bucket.list_blobs(prefix='images/'))

    print(f'Found {len(blobs)} images')

    # Start from the 1045th image
    blobs = blobs[2670:]

    updated_images = 0

    for blob in tqdm(blobs, desc="Processing images"):
        if blob.name.endswith(('.png', '.jpg', '.jpeg')):
            image_data = blob.download_as_bytes()
            # Remove the background
            try:
                processed_image_data = remove_background(image_data)
            except Exception as e:
                print(f"Error removing background from image {blob.name}: {e}")
                continue

            # Upload the processed image back to Firebase Storage
            processed_blob = bucket.blob(f'processed_images/{blob.name.split("/")[-1]}')
            processed_blob.upload_from_string(processed_image_data, content_type='image/png')

            updated_images += 1

    print(f'Updated {updated_images} images')


@command
def update_alc_images_to_bgless_path():
    alcohols_ref = db.collection('Alcohols')
    docs = list(alcohols_ref.stream())
    print('number of docs:', len(docs))

    alcohols_updated = 0

    for doc in tqdm(docs, desc="Processing alcohols"):
        alcohol_data = doc.to_dict()
        # Check if there's a 'image' field
        if 'image' in alcohol_data:
            # Replace 'images' with 'processed_images' in the image URL
            alcohol_data['image'] = alcohol_data['image'].replace('images', 'processed_images')
            # Update the document in Firestore
            alcohols_ref.document(doc.id).set(alcohol_data)
            alcohols_updated += 1

    print(f'Updated {alcohols_updated} alcohols')


@command
def update_alcohol_base_spirit():
    base_spirits = [
        'Irish Whiskey',
        'American Whiskey',
        'Scotch Whisky',
        'Canadian Whisky',
        'Japanese Whisky',
        'Bourbon',
        'Blanco Tequila',
        'Repos ado Tequila',
        'Anjo Tequila',
        'Vodka',
        'London Dry Gin',
        'Floral Gin',
        'Botanical Gin',
        'White Rum',
        'Gold Rum',
        'Dark Rum',
        'Spiced Rum',
        'Mescal',
        'Grappa',
        'Pisco',
        'None'
    ]

    alcohols_ref = db.collection('Alcohols')
    docs = list(alcohols_ref.stream())
    print('number of docs:', len(docs))

    alcohols_updated = 0

    for doc in tqdm(docs, desc="Processing alcohols"):
        alcohol_data = doc.to_dict()
        # Check if there's a 'spiritType' field
        if 'baseSpirit' in alcohol_data:
            # ask openai to set the baseSpirit
            system_prompt = f"Given the following alcohol, please ONLY return one of the following options: {base_spirits}. If the alcohol does not fit into any of these categories, please return 'None'."
            user_prompt = f'{alcohol_data["name"], alcohol_data["description"], alcohol_data["brand"], alcohol_data["country"]}'
            alcohol_data['baseSpirit'] = askOpenAI(system_prompt, user_prompt)
            # Update the document in Firestore
            alcohols_ref.document(doc.id).set(alcohol_data)
            alcohols_updated += 1

    print(f'Updated {alcohols_updated} alcohols')

@command
def update_cocktail_ingredients_spirit():
    base_spirits = [
        'Irish Whiskey',
        'American Whiskey',
        'Scotch Whisky',
        'Canadian Whisky',
        'Japanese Whisky',
        'Bourbon',
        'Blanco Tequila',
        'Repos ado Tequila',
        'Anjo Tequila',
        'Vodka',
        'London Dry Gin',
        'Floral Gin',
        'Botanical Gin',
        'White Rum',
        'Gold Rum',
        'Dark Rum',
        'Spiced Rum',
        'Mescal',
        'Grappa',
        'Pisco',
        'None'
    ]

    cocktails_ref = db.collection('cocktails')
    docs = list(cocktails_ref.stream())
    print('number of docs:', len(docs))

    cocktails_updated = 0

    for doc in tqdm(docs, desc="Processing cocktails"):
        cocktail_data = doc.to_dict()
        # Check if there's a 'spiritType' field
        if 'ingredients' in cocktail_data:
            for ingredient in cocktail_data['ingredients']:
                if 'isSpirit' in ingredient:
                    # ask openai to set the baseSpirit
                    system_prompt = f"Given the following alcohol, please ONLY return one of the following options: {base_spirits}, with no quotes. If the alcohol does not fit into any of these categories, please return 'None'."
                    user_prompt = f'{ingredient}'
                    ingredient.pop('baseSpirit', None)
                    ingredient['spiritType'] = askOpenAI(system_prompt, user_prompt)
                    # Update the document in Firestore
                    cocktails_ref.document(doc.id).set(cocktail_data)
                    cocktails_updated += 1


@command
def remove_bloat():
    alcohols_ref = db.collection('Alcohols')
    docs = list(alcohols_ref.stream())
    print('number of docs:', len(docs))

    quantity_alcohols_deleted = 0
    size_alcohols_deleted = 0
    image_alcohols_deleted = 0

    for doc in tqdm(docs, desc="Processing alcohols"):
        alcohol_data = doc.to_dict()
        # Check if there's a 'spiritType' field
        if ' x ' in alcohol_data['name']:
            # delete the document
            alcohols_ref.document(doc.id).delete()
            # Update the document in Firestore
            quantity_alcohols_deleted += 1

        if 'Case' in alcohol_data['name']:
            # delete the document
            alcohols_ref.document(doc.id).delete()
            # Update the document in Firestore
            quantity_alcohols_deleted += 1

        if alcohol_data['size'] == 0:
            # delete the document
            alcohols_ref.document(doc.id).delete()
            # Update the document in Firestore
            size_alcohols_deleted += 1

        if not alcohol_data['image']:
            # delete the document
            alcohols_ref.document(doc.id).delete()
            # Update the document in Firestore
            image_alcohols_deleted += 1

    print(f'Deleted {quantity_alcohols_deleted} quantity alcohols, {size_alcohols_deleted} no size alcohols, {image_alcohols_deleted} no image alcohols')

@command
def standardise_base_spirit_quotes():
    alcohols_ref = db.collection('Alcohols')
    docs = list(alcohols_ref.stream())
    print('number of docs:', len(docs))

    alcohols_updated = 0

    for doc in tqdm(docs, desc="Processing alcohols"):
        alcohol_data = doc.to_dict()
        # Check if there's a 'baseSpirit' field
        if 'baseSpirit' in alcohol_data:
            # Replace single quotes with double quotes
            alcohol_data['baseSpirit'] = alcohol_data['baseSpirit'].replace("'", '')
            # Update the document in Firestore
            alcohols_ref.document(doc.id).set(alcohol_data)
            alcohols_updated += 1

    print(f'Updated {alcohols_updated} alcohols')


@command
def make_and_set_image_blur_hash():
    # cocktails_ref = db.collection('cocktails')
    # docs = list(cocktails_ref.stream())
    # print('number of docs:', len(docs))
    #
    # cocktails_updated = 0
    #
    # for doc in tqdm(docs, desc="Processing cocktails"):
    #     cocktail_data = doc.to_dict()
    #     # Check if there's a 'image' field
    #     if 'image' in cocktail_data:
    #         # Get the image data
    #         image_data = requests.get(cocktail_data['image']).content
    #         # Open the image with PIL
    #         image = Image.open(BytesIO(image_data))
    #         # If the image has an alpha channel, replace it with white
    #         if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
    #             image = image.convert("RGBA")
    #             r, g, b, a = image.split()
    #             rgb_image = Image.merge('RGB', (r, g, b))
    #
    #             mask = Image.new('L', image.size, 255)
    #             mask.paste(a, (0,0), a)
    #
    #             image = Image.composite(rgb_image, Image.new('RGB', image.size, 'white'), mask)
    #         # Get the blur hash
    #         blur_hash = blurhash.encode(image, x_components=4, y_components=3)
    #         # Set the blur hash
    #         cocktail_data['imageBlurHash'] = blur_hash
    #         # Update the document in Firestore
    #         cocktails_ref.document(doc.id).set(cocktail_data)
    #         cocktails_updated += 1
    #
    # print(f'Updated {cocktails_updated} cocktails')

    alcohols_ref = db.collection('Alcohols')
    docs = list(alcohols_ref.stream())
    print('number of docs:', len(docs))

    alcohols_updated = 0

    for doc in tqdm(docs, desc="Processing alcohols"):
        alcohol_data = doc.to_dict()
        # Check if there's a 'image' field
        if 'image' in alcohol_data:
            # Get the image data
            response = requests.get(alcohol_data['image'])
            if response.status_code != 200:
                print(f"Unable to retrieve image from {alcohol_data['image']}")
                continue
            image_data = response.content
            # Open the image with PIL
            try:
                image = Image.open(BytesIO(image_data))
            except PIL.UnidentifiedImageError:
                print(f"Unable to identify image from {alcohol_data['image']}")
                continue
            # If the image has an alpha channel, replace it with white
            if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
                image = image.convert("RGBA")
                r, g, b, a = image.split()
                rgb_image = Image.merge('RGB', (r, g, b))

                mask = Image.new('L', image.size, 255)
                mask.paste(a, (0,0), a)

                image = Image.composite(rgb_image, Image.new('RGB', image.size, 'white'), mask)
            # Get the blur hash
            blur_hash = blurhash.encode(image, x_components=4, y_components=3)
            # Set the blur hash
            alcohol_data['imageBlurHash'] = blur_hash
            # Update the document in Firestore
            alcohols_ref.document(doc.id).set(alcohol_data)
            alcohols_updated += 1

    print(f'Updated {alcohols_updated} alcohols')

@command
def rewrite_alcohol_description():
    alcohols_ref = db.collection('Alcohols')
    docs = list(alcohols_ref.stream())
    print('number of docs:', len(docs))

    alcohols_updated = 0

    for doc in tqdm(docs, desc="Processing alcohols"):
        alcohol_data = doc.to_dict()
        # Check if there's a 'description' field
        if 'description' in alcohol_data:
            # ask openai to summarise the description
            system_prompt = 'rewrite the given sentence into a more concise and readable sentence, exclude any mention of VIP bottles and return only the new sentence'
            user_prompt = f'{alcohol_data["description"]}'
            alcohol_data['oldDescription'] = alcohol_data['description']
            alcohol_data['description'] = askOpenAI(system_prompt, user_prompt)
            # Update the document in Firestore
            alcohols_ref.document(doc.id).set(alcohol_data)
            alcohols_updated += 1

    print(f'Updated {alcohols_updated} alcohols')

@command
def format_cocktail_images():
    blobs = list(bucket.list_blobs(prefix='cocktail_images/'))

    print(f'Found {len(blobs)} cocktail images')

    updated_images = 0

    for blob in tqdm(blobs, desc="modifying cocktail images"):
        if blob.name.endswith(('.png', '.jpg', '.jpeg')):
            image_data = blob.download_as_bytes()
            # Remove the background
            try:
                processed_image_data = move_image_to_bottom(image_data)
            except Exception as e:
                print(f"Error modifying image {blob.name}: {e}")
                continue

            # Upload the processed image back to Firebase Storage
            processed_blob = bucket.blob(f'modified_cocktail_images/{blob.name.split("/")[-1]}')
            processed_blob.upload_from_string(processed_image_data, content_type='image/png')

            updated_images += 1

    print(f'Updated {updated_images} images')


# End of the patches

@click.command()
@click.argument('command', type=click.Choice([c.__name__ for c in commands]))
def patch(command):
    command_lookup = {c.__name__: c for c in commands}

    start = datetime.now()
    command_lookup[command]()

    print(f'Patch took {(datetime.now() - start).total_seconds():0.2f}s')


if __name__ == '__main__':
    patch()

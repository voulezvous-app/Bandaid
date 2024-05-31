import json
from datetime import datetime

import requests
from devtools import debug
from tqdm import tqdm

from firebase_setup import db
from openai_setup import client, askOpenAI

import click

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
                if 'isLiquor' in ingredient and ingredient['isLiquor']:
                    # Change 'isLiquor' to 'isLiqueur'
                    ingredient['isLiqueur'] = ingredient.pop('isLiquor')

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
        tags_json = requests.get('https://gist.githubusercontent.com/PrenSJ2/91acf1ae805de805bbaf521b62e7dfc7/raw/35a7d769f45ad263e2556d14881d656a08bb6e72/vv_tags')
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

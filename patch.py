from datetime import datetime
from devtools import debug

from firebase_setup import db
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

from datetime import datetime

from firebase_setup import db
import click

commands = []

def command(func):
    commands.append(func)
    return func

# Start of the patches


# End of the patches

@click.command()
@click.argument('command', type=click.Choice([c.__name__ for c in commands]))
def patch(command):
    command_lookup = {c.__name__: c for c in commands}

    start = datetime.now()
    doc_ref = db.collection('collection_name').document('document_id')
    db.run_transaction(lambda transaction: command_lookup[command](transaction, doc_ref))

    print(f'Patch took {(datetime.now() - start).total_seconds():0.2f}s')

if __name__ == '__main__':
    patch()
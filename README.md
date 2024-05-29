# Bandaid
A simple tool to write patches for the VoulezVous Firestore database.

## Setup
- Create a virtual environment and install the dependencies.
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Create a patch
- In the `patch.py` file, create a new function that will be your patch.
- The function needs to be made between the `# Start of patches` and `# End of patches`.
- The function needs to have the `@command` decorator.

## Usage
- To run a patch use the following command:
```bash
python patch.py <patch_name>
```
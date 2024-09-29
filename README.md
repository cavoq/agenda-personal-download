# agenda-personal-download

Script to download and save all relevant salary documents from https://agenda-personal-portal.de

## Usage

1. Install the requirements with `pip install -r requirements.txt`
2. (Optional) Create virtual environment with `python -m venv venv` and activate it with `source venv/bin/activate`
2. Run the script with `python download.py`

## Configuration

The following environment variables are required:

- `EMAIL`: Your email address for the portal
- `PASSWORD`: Your password for the portal
- `DOWNLOAD_PATH`: The path where the files should be saved

You may create a `.env` file in the root directory of the project to set these variables.
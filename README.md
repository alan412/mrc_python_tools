# MRC Python Tools

## To generate JSON for the robotpy modules and classes:

The following instructions work on macOS Sonoma 14.6.1.

### Setup
    1. cd <your repo>/mrc_python_tools
    1. python3.12 -m venv ./venv
    1. source ./venv/bin/activate
    1. python3.12 -m pip install -r src/requirements.txt
    1. deactivate

### Examine the robotpy modules and classes (optional)
    1. cd <your repo>/mrc_python_tools
    1. python3.12 -m venv ./venv
    1. source ./venv/bin/activate
    1. cd src/examine
    1. python3.12 examine.py --output_directory=../../output
    1. deactivate

### Generate JSON
    1. cd <your repo>/mrc_python_tools
    1. python3.12 -m venv ./venv
    1. source ./venv/bin/activate
    1. cd src/generate_json
    1. python3.12 generate_json.py --output_directory=../../output
    1. deactivate

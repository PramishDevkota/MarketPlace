#!/bin/bash
# Install dependencies overriding uv/PEP 668 restriction
python3 -m pip install --break-system-packages -r requirements.txt

# Run collectstatic
python3 manage.py collectstatic --noinput --clear
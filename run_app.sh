#!/bin/bash
# Script to run the Interac e-Transfer web app

cd "$(dirname "$0")"
source venv/bin/activate
python3 app.py


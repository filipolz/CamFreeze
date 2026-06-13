#!/bin/zsh
# Launch CamFreeze using the project's virtual environment.
cd "$(dirname "$0")"
exec ./venv/bin/python app.py

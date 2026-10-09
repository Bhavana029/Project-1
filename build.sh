#!/usr/bin/env bash
# Render build — dependencies and static files (no SQL migrations; auth is in MongoDB).
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput

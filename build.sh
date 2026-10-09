#!/usr/bin/env bash
# Render build script — install deps, collect static files, migrate Django DB (PostgreSQL on Render).
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

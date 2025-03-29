#!/bin/bash
set -e

# Adjust if your project lives somewhere else
PROJECT_DIR="/home/django_user/jobs_manager"

cd "$PROJECT_DIR"
source .venv/bin/activate


# Pull the latest code from Git
git pull

# If needed, install new dependencies (generally these don't change)

npm install

poetry install

# Apply Django migrations & collectstatic
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --clear --noinput
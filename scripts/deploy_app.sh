#!/bin/bash
set -e

# Detect environment
if [ -d "/home/django_user/jobs_manager" ]; then
    PROJECT_DIR="/home/django_user/jobs_manager"
elif [ -d "/opt/workflow_app/jobs_manager" ]; then
    PROJECT_DIR="/opt/workflow_app/jobs_manager"
else
    echo "ERROR: Project directory not found"
    exit 1
fi

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

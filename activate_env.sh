#!/bin/bash
# Script to activate the correct virtual environment for Jobs Manager

# Activate the virtual environment
source "$(dirname "$0")/venv/bin/activate"

# Print confirmation
echo "Jobs Manager environment activated!"
echo "Python version: $(python --version)"
echo "Environment path: $VIRTUAL_ENV"

# Optional: Set any environment variables needed
# export DJANGO_SETTINGS_MODULE=jobs_manager.settings.local

# Provide helpful commands
echo ""
echo "Available commands:"
echo "  python manage.py runserver       # Start development server"
echo "  python manage.py migrate         # Apply database migrations"
echo "  python manage.py shell           # Open Django shell"
echo "  deactivate                       # Exit virtual environment"
#!/usr/bin/env bash
set -euo pipefail

# load your project venv
source /home/django_user/jobs_manager/.venv/bin/activate

# run the cleanup (pass --delete to actually purge)
exec python /usr/local/bin/cleanup_backups.py "$@"

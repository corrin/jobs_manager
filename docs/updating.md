# Updating the Application

This guide covers updating an existing installation to the latest version. For first-time setup, see [initial_install.md](initial_install.md).

## Development Environment

If you're running the application locally for development:

1. Pull the latest code:
   ```bash
   git pull
   ```

2. Update dependencies:
   ```bash
   npm install
   poetry install
   ```

3. Apply any database changes:
   ```bash
   python manage.py migrate
   ```

4. Update static files:
   ```bash
   python manage.py collectstatic --noinput
   ```

5. Restart the development server if running

## Production-like Environment

For servers running with Gunicorn and requiring Xero integration:

1. Ensure you have sudo access and the required backup directories exist:
   ```bash
   sudo mkdir -p /var/backups/jobs_manager
   ```

2. Run the deployment script:
   ```bash
   sudo /path/to/adhoc/deploy_release.sh
   ```

   This script will:
   - Back up the current code and database
   - Copy backups to Google Drive
   - Pull latest code
   - Update dependencies
   - Apply migrations
   - Collect static files
   - Restart Gunicorn

### Manual Update (if needed)

If you need to update manually on a production-like system:

1. Back up the database:
   ```bash
   mysqldump -u root jobs_manager | gzip > /var/backups/jobs_manager/db_$(date +%Y%m%d_%H%M%S).sql.gz
   ```

2. Back up the code:
   ```bash
   tar -zcf /var/backups/jobs_manager/code_$(date +%Y%m%d_%H%M%S).tgz -C /home/django_user --exclude='gunicorn.sock' jobs_manager
   ```

3. Switch to the application user:
   ```bash
   su - django_user
   ```

4. Update and restart:
   ```bash
   cd /home/django_user/jobs_manager
   source .venv/bin/activate
   git pull
   npm install
   poetry install
   python manage.py migrate
   python manage.py collectstatic --noinput
   exit  # back to root
   systemctl restart gunicorn
   ```

## Troubleshooting

If you encounter issues after updating:

1. Check the logs:
   - SQL logs: `logs/debug_sql.log`
   - Xero integration: `logs/xero_integration.log`

2. Verify database migrations:
   ```bash
   python manage.py showmigrations workflow
   ```

3. For production environments, you can rollback using:
   ```bash
   sudo /path/to/adhoc/rollback_release.sh
   ```

4. If static files aren't loading, try:
   ```bash
   python manage.py collectstatic --clear --noinput

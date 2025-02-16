from django.db import migrations
import os
from pathlib import Path

def create_systemd_service(apps, schema_editor):
    """
    Create the systemd service file for Xero sync if it doesn't exist.
    """
    service_path = Path('/etc/systemd/system/xero-sync.service')
    
    # Only proceed if we're in a production environment
    if not service_path.parent.exists():
        return

    if not service_path.exists():
        service_content = """[Unit]
Description=Xero Sync Service
After=network.target

[Service]
Type=simple
User=django_user
Group=django_user
WorkingDirectory=/home/django_user/jobs_manager
Environment=DJANGO_SETTINGS_MODULE=jobs_manager.settings.production_like
ExecStart=/home/django_user/jobs_manager/.venv/bin/python manage.py start_xero_sync
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
"""
        # Write service file
        try:
            with open(service_path, 'w') as f:
                f.write(service_content)
            
            # Set up the service
            os.system('systemctl daemon-reload')
            os.system('systemctl enable xero-sync')
            os.system('systemctl restart xero-sync')
        except Exception as e:
            print(f"Warning: Could not set up Xero sync service: {e}")
            print("You may need to manually set up the service in production")

def remove_systemd_service(apps, schema_editor):
    """
    Remove the systemd service file if it exists.
    """
    service_path = Path('/etc/systemd/system/xero-sync.service')
    if service_path.exists():
        try:
            os.system('systemctl stop xero-sync')
            os.system('systemctl disable xero-sync')
            service_path.unlink()
            os.system('systemctl daemon-reload')
        except Exception as e:
            print(f"Warning: Could not remove Xero sync service: {e}")

class Migration(migrations.Migration):
    dependencies = [
        ('workflow', '0081_add_last_xero_deep_sync'),
    ]

    operations = [
        migrations.RunPython(
            create_systemd_service,
            reverse_code=remove_systemd_service
        ),
    ]
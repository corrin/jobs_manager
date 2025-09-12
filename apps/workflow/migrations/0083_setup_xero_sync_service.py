import logging
import platform
import subprocess
from pathlib import Path

from django.db import migrations

logger = logging.getLogger(__name__)


def create_systemd_service(apps, schema_editor):
    """
    Attempts to set up the Xero sync service, falling back to instructions if sudo fails.
    """
    # Skip if not on Linux
    if platform.system() != "Linux":
        logger.info("Not on Linux, skipping systemd service setup")
        return

    service_path = Path("/etc/systemd/system/xero-sync.service")

    # Only proceed if we're in a production environment
    if not service_path.parent.exists():
        logger.info(
            "Not in production environment (no /etc/systemd), skipping service setup"
        )
        return

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
WantedBy=multi-user.target"""

    # Try using sudo first
    try:
        # Test if we have sudo access
        test_sudo = subprocess.run(
            ["sudo", "-n", "true"], capture_output=True, text=True
        )

        if test_sudo.returncode == 0:
            # We have sudo access, proceed with automatic setup
            subprocess.run(
                ["sudo", "bash", "-c", f"cat > {service_path}"],
                input=service_content.encode(),
                check=True,
            )
            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
            subprocess.run(["sudo", "systemctl", "enable", "xero-sync"], check=True)
            subprocess.run(["sudo", "systemctl", "restart", "xero-sync"], check=True)
            logger.info("Successfully set up Xero sync service")
            return
    except Exception as e:
        logger.error(f"Automatic setup failed: {e}")

    # If we get here, either sudo failed or we don't have access
    logger.info("\nTo set up the Xero sync service, run these commands as root:")
    logger.info("\n# Create service file")
    logger.info(
        f"cat > /etc/systemd/system/xero-sync.service << 'EOL'\n{service_content}\nEOL"
    )
    logger.info("\n# Reload systemd and start service")
    logger.info("systemctl daemon-reload")
    logger.info("systemctl enable xero-sync")
    logger.info("systemctl start xero-sync")
    logger.info("\n# Verify it's running")
    logger.info("systemctl status xero-sync")


def remove_systemd_service(apps, schema_editor):
    """
    Attempts to remove the Xero sync service, falling back to instructions if sudo fails.
    """
    if platform.system() != "Linux":
        return

    service_path = Path("/etc/systemd/system/xero-sync.service")
    if not service_path.exists():
        return

    try:
        # Test if we have sudo access
        test_sudo = subprocess.run(
            ["sudo", "-n", "true"], capture_output=True, text=True
        )

        if test_sudo.returncode == 0:
            # We have sudo access, proceed with automatic removal
            subprocess.run(["sudo", "systemctl", "stop", "xero-sync"], check=True)
            subprocess.run(["sudo", "systemctl", "disable", "xero-sync"], check=True)
            subprocess.run(["sudo", "rm", str(service_path)], check=True)
            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
            logger.info("Successfully removed Xero sync service")
            return
    except Exception as e:
        logger.error(f"Automatic removal failed: {e}")

    # If we get here, either sudo failed or we don't have access
    logger.info("\nTo remove the Xero sync service, run these commands as root:")
    logger.info("systemctl stop xero-sync")
    logger.info("systemctl disable xero-sync")
    logger.info("rm /etc/systemd/system/xero-sync.service")
    logger.info("systemctl daemon-reload")


class Migration(migrations.Migration):
    dependencies = [
        ("workflow", "0082_add_last_xero_deep_sync"),
    ]

    operations = [
        migrations.RunPython(
            create_systemd_service, reverse_code=remove_systemd_service
        ),
    ]

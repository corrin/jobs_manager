import os
import shlex
import subprocess
from typing import Any

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Starts ngrok tunnel using the ngrok CLI"

    def handle(self, *args: Any, **kwargs: Any) -> None:
        app_domain = os.environ.get("APP_DOMAIN", "msm-workflow.ngrok-free.app")
        django_port = os.environ.get("DJANGO_PORT", "8000")

        # Create ngrok command with the custom domain
        ngrok_command = (
            f"ngrok http --domain={app_domain} --pooling-enabled {django_port}"
        )

        # Start ngrok process
        self.stdout.write(
            self.style.SUCCESS(f"Starting ngrok with command: '{ngrok_command}'...")
        )
        # We don't capture the process, just launch it.
        # It will run until manually stopped or the parent terminal closes.
        try:
            subprocess.Popen(shlex.split(ngrok_command))
            self.stdout.write(
                self.style.SUCCESS(
                    "ngrok process launched. Check the ngrok console/UI for status."
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "This command only launches ngrok. It does not block or wait. "
                    "Run the Django server separately if needed."
                )
            )
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(
                    "Error: 'ngrok' command not found. "
                    "Make sure ngrok is installed and in your system's PATH."
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to launch ngrok process: {e}"))

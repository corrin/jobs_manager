import os
import shlex
import subprocess
from typing import Any

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Starts Django server with ngrok"

    def handle(self, *args: Any, **kwargs: Any) -> None:
        ngrok_domain = os.environ.get("NGROK_DOMAIN", "msm-workflow.ngrok-free.app")
        django_port = os.environ.get("DJANGO_PORT", "8000")

        # Create ngrok command with the custom domain
        ngrok_command = f"ngrok http  --region=au --domain={ngrok_domain} {django_port}"

        # Start ngrok process
        self.stdout.write(
            self.style.SUCCESS(f"Starting ngrok with domain {ngrok_domain}...")
        )
        # We don't bother capturing the ngrok process because it runs indefinitely
        # ngrok_process = subprocess.Popen(shlex.split(ngrok_command))
        subprocess.Popen(shlex.split(ngrok_command))

        # # Run Django development server
        # self.stdout.write(
        #     self.style.SUCCESS(f"Starting Django server on port {django_port}...")
        # )
        #os.system(f"python manage.py runserver {django_port}")

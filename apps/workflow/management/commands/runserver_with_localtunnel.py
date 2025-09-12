import os
import subprocess
from typing import Any

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Starts Django server with localtunnel"

    def handle(self, *args: Any, **kwargs: Any) -> None:
        app_domain = os.environ.get("APP_DOMAIN", "msm-your-user-name.loca.lt")
        django_port = os.environ.get("DJANGO_PORT", "8000")

        # Extract subdomain from full domain
        subdomain = app_domain.split(".")[0] if "." in app_domain else app_domain

        # Create localtunnel command with the custom subdomain
        lt_command = f"lt --port {django_port} --subdomain {subdomain}"

        # Start localtunnel process
        self.stdout.write(
            self.style.SUCCESS(f"Starting localtunnel with domain {app_domain}...")
        )
        # We don't bother capturing the lt process because it runs indefinitely
        subprocess.Popen(lt_command.split())

        # # Run Django development server
        # self.stdout.write(
        #     self.style.SUCCESS(f"Starting Django server on port {django_port}...")
        # )
        # os.system(f"python manage.py runserver {django_port}")

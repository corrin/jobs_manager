import os
import subprocess
from typing import Any

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Update __init__.py files in specified directories"

    def handle(self, *args: Any, **kwargs: Any) -> None:
        # List of directories to update
        folders_to_update = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../views")),
        ]

        # Path to the standalone Python script
        update_script = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../adhoc/update_init.py")
        )

        # Loop through each folder and call the standalone script
        for folder in folders_to_update:
            if os.path.exists(folder):
                self.stdout.write(self.style.WARNING(f"Updating folder: {folder}"))
                subprocess.run(["python", update_script, folder])
            else:
                self.stdout.write(
                    self.style.WARNING(f"Skipping non-existent folder: {folder}")
                )

        self.stdout.write(self.style.SUCCESS("Successfully updated __init__.py files"))

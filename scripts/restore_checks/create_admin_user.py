#!/usr/bin/env python
"""Create default admin user for development."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")

import django

django.setup()

from apps.accounts.models import Staff

EMAIL = "defaultadmin@example.com"
PASSWORD = "Default-admin-password"

if Staff.objects.filter(email=EMAIL).exists():
    print(f"Admin user already exists: {EMAIL}")
else:
    user = Staff.objects.create_user(
        email=EMAIL,
        password=PASSWORD,
        first_name="Default",
        last_name="Admin",
    )
    user.is_office_staff = True
    user.is_superuser = True
    user.save()
    print(f"Created admin user: {user.email}")

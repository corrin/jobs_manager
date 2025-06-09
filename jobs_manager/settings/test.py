from .base import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Simplify environment for tests
INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in [
    "debug_toolbar",
    "django_apscheduler",
]]

STATIC_URL = "/static/"

# Ensure required env vars have defaults for tests
import os
SECRET_KEY = os.getenv("SECRET_KEY", "test")
DROPBOX_WORKFLOW_FOLDER = os.getenv("DROPBOX_WORKFLOW_FOLDER", "/tmp")
XERO_CLIENT_ID = os.getenv("XERO_CLIENT_ID", "x")
XERO_CLIENT_SECRET = os.getenv("XERO_CLIENT_SECRET", "x")
XERO_REDIRECT_URI = os.getenv("XERO_REDIRECT_URI", "http://localhost")

os.environ.setdefault("DISABLE_APPSCHEDULER", "1")

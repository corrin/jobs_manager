import pytest
from django.conf import settings


@pytest.fixture(autouse=True)
def _use_sqlite_db(settings):
    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }


@pytest.fixture(autouse=True)
def _set_required_env_vars(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DROPBOX_WORKFLOW_FOLDER", "tmp")
    monkeypatch.setenv("XERO_CLIENT_ID", "x")
    monkeypatch.setenv("XERO_CLIENT_SECRET", "x")
    monkeypatch.setenv("XERO_REDIRECT_URI", "http://example.com")

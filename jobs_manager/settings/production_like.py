from dotenv import load_dotenv

from .base import *  # noqa: F403
from .local import STATIC_ROOT as LOCAL_STATIC_ROOT

# Production like is for things like ngnix, Redis, celery, etc.
# NOTE: With Redis and Celery removed, I believe that local and production are now the same
# I've kept this because it was working previously but I odn't think it matters going forward
load_dotenv(BASE_DIR / ".env")

DEBUG = False

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "debug_toolbar"]

MIDDLEWARE = [
    mw for mw in MIDDLEWARE if mw != "debug_toolbar.middleware.DebugToolbarMiddleware"
]

STATIC_URL = "/static/"
STATIC_ROOT = os.getenv("STATIC_ROOT", LOCAL_STATIC_ROOT)

# Security configs
SESSION_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# CSRF configs
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = [
    "http://" + host for host in ALLOWED_HOSTS if host not in ["localhost", "127.0.0.1"]
]
CSRF_TRUSTED_ORIGINS += ["http://localhost", "http://127.0.0.1"]
CSRF_TRUSTED_ORIGINS += [
    "https://" + host
    for host in ALLOWED_HOSTS
    if host not in ["localhost", "127.0.0.1"]
]

# Cache configs
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

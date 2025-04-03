from dotenv import load_dotenv

from .base import *  # noqa: F403
from .local import STATIC_ROOT as LOCAL_STATIC_ROOT

# Production like is for things like ngnix, Redis, celery, etc.
# Let's keep it because it'll be needed to reset user passwords
load_dotenv(BASE_DIR / ".env")

DEBUG = False

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]

INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "debug_toolbar"]

MIDDLEWARE = [
    mw for mw in MIDDLEWARE if mw != "debug_toolbar.middleware.DebugToolbarMiddleware"
]

STATIC_URL = "/static/"
STATIC_ROOT = os.getenv("STATIC_ROOT", LOCAL_STATIC_ROOT)

# Use ManifestStaticFilesStorage to add hashes to static files
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'user_attributes': ('email', 'first_name', 'last_name', 'preferred_name'),
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 10,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

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

# Password change email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST","smtp.google.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
EMAIL_BCC = os.getenv("EMAIL_BCC", "").split(",")

from django.apps import apps
from django.db import ProgrammingError

def configure_site_for_environment():
    try:
        if apps.is_installed('django.contrib.sites'):
            Site = apps.get_model('sites', 'Site')
            current_domain = os.getenv("DJANGO_SITE_DOMAIN")
            current_name = "Jobs Manager"
            
            try:
                site = Site.objects.get(pk=SITE_ID)
                if site.domain != current_domain or site.name != current_name:
                    site.domain = current_domain
                    site.name = current_name
                    site.save()
            except Site.DoesNotExist:
                Site.objects.create(
                    pk=SITE_ID,
                    domain=current_domain,
                    name=current_name
                )
    except ProgrammingError:
        pass
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error configuring the site: {e}")

from django.core.signals import request_started
request_started.connect(lambda **kwargs: configure_site_for_environment(), weak=False, dispatch_uid="configure_site")

PASSWORD_RESET_TIMEOUT = 86400  # 24 hours in seconds

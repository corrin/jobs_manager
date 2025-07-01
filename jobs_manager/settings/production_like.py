from dotenv import load_dotenv

from .base import *  # noqa: F403
from .local import MEDIA_ROOT as LOCAL_MEDIA_ROOT
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

MEDIA_URL = "/media/"
MEDIA_ROOT = os.getenv("MEDIA_ROOT", LOCAL_MEDIA_ROOT)

# Use ManifestStaticFilesStorage to add hashes to static files
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {
            "user_attributes": ("email", "first_name", "last_name", "preferred_name"),
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 10,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Security configs
SESSION_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# Proxy/Load Balancer Configuration for UAT
# Trust the proxy headers to determine HTTPS status
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# CSRF configs
CSRF_COOKIE_SECURE = True

# Load CSRF trusted origins from environment
cors_trusted_origins_env = os.getenv("CORS_TRUSTED_ORIGINS", "")
if cors_trusted_origins_env:
    CSRF_TRUSTED_ORIGINS = [
        origin.strip()
        for origin in cors_trusted_origins_env.split(",")
        if origin.strip()
    ]
else:
    # Fallback to building from ALLOWED_HOSTS
    CSRF_TRUSTED_ORIGINS = [
        "http://" + host
        for host in ALLOWED_HOSTS
        if host not in ["localhost", "127.0.0.1"]
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
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.google.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
EMAIL_BCC = os.getenv("EMAIL_BCC", "").split(",")

# Admin email notifications for errors
ADMINS = [
    (name, email)
    for name_email in os.getenv("DJANGO_ADMINS", "").split(",")
    if (parts := name_email.strip().split(":")) and len(parts) == 2
    for name, email in [parts]
]

# Admin email notifications for errors
ADMINS = [
    (name, email)
    for name_email in os.getenv("DJANGO_ADMINS", "").split(",")
    if (parts := name_email.strip().split(":")) and len(parts) == 2
    for name, email in [parts]
]

# CORS Configuration - Load from environment variables
cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
if cors_origins_env:
    CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in cors_origins_env.split(",") if origin.strip()
    ]
else:
    # No fallback in production - must be explicitly set in .env
    CORS_ALLOWED_ORIGINS = []

# Add ngrok domain from environment if available
ngrok_domain = os.getenv("NGROK_DOMAIN")
if ngrok_domain and ngrok_domain not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(ngrok_domain)

# Add regex patterns for ngrok domains - load from environment if needed
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.ngrok\.io$",
    r"^https://.*\.ngrok-free\.app$",
]

CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "True").lower() == "true"

# CORS Allowed Headers - read from environment or use defaults
cors_headers_env = os.getenv("CORS_ALLOWED_HEADERS", "")
if cors_headers_env:
    CORS_ALLOWED_HEADERS = [
        header.strip() for header in cors_headers_env.split(",") if header.strip()
    ]
else:
    CORS_ALLOWED_HEADERS = [
        "accept",
        "accept-encoding",
        "authorization",
        "content-type",
        "dnt",
        "origin",
        "user-agent",
        "x-csrftoken",
        "x-requested-with",
        "x-actual-users",  # Custom header for staff filtering - should be X-Actual-Users
        "X-Actual-Users",  # Case sensitive version for proper CORS support
    ]

# Enable JWT Authentication for API - Load from environment
ENABLE_JWT_AUTH = os.getenv("ENABLE_JWT_AUTH", "True").lower() == "true"
ENABLE_DUAL_AUTHENTICATION = (
    os.getenv("ENABLE_DUAL_AUTHENTICATION", "False").lower() == "true"
)

# JWT Configuration for production - override base settings for secure cookies
if ENABLE_JWT_AUTH:
    from .base import SIMPLE_JWT as BASE_SIMPLE_JWT

    SIMPLE_JWT = BASE_SIMPLE_JWT.copy()
    SIMPLE_JWT.update(
        {
            "AUTH_COOKIE_SECURE": True,  # Require HTTPS for auth cookies in production
            "AUTH_COOKIE_HTTP_ONLY": True,  # httpOnly for security
            "AUTH_COOKIE_SAMESITE": "Lax",
            "AUTH_COOKIE_DOMAIN": None,  # Let browser determine based on request domain
            "REFRESH_COOKIE": "refresh_token",
            "REFRESH_COOKIE_SECURE": True,  # Require HTTPS for refresh cookies
            "REFRESH_COOKIE_HTTP_ONLY": True,
            "REFRESH_COOKIE_SAMESITE": "Lax",
        }
    )

from django.apps import apps
from django.db import ProgrammingError


def configure_site_for_environment():
    try:
        if apps.is_installed("django.contrib.sites"):
            Site = apps.get_model("sites", "Site")
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
                    pk=SITE_ID, domain=current_domain, name=current_name
                )
    except ProgrammingError:
        pass
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error configuring the site: {e}")


from django.core.signals import request_started

request_started.connect(
    lambda **kwargs: configure_site_for_environment(),
    weak=False,
    dispatch_uid="configure_site",
)

PASSWORD_RESET_TIMEOUT = 86400  # 24 hours in seconds

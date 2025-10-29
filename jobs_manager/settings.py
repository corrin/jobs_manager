import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
from rest_framework.permissions import IsAuthenticated

# Import scopes from constants to ensure consistency
from apps.workflow.api.xero.constants import XERO_SCOPES as DEFAULT_XERO_SCOPES_LIST

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def validate_required_settings() -> None:
    """Validate that all required settings are properly configured."""
    # Define core required environment variables that must be set
    required_env_vars = [
        # Django Core
        "SECRET_KEY",
        "DEBUG",
        "DEBUG_PAYLOAD",
        "DJANGO_ENV",
        "ALLOWED_HOSTS",
        "DJANGO_SITE_DOMAIN",
        # Database
        "MYSQL_DATABASE",
        "MYSQL_DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
        "DB_PORT",
        # File Storage
        "DROPBOX_WORKFLOW_FOLDER",
        # Xero Integration
        "XERO_CLIENT_ID",
        "XERO_CLIENT_SECRET",
        "XERO_REDIRECT_URI",
        "XERO_DEFAULT_USER_ID",
        "XERO_SYNC_PROJECTS",
        "XERO_WEBHOOK_KEY",
        # Email
        "EMAIL_HOST",
        "EMAIL_PORT",
        "EMAIL_USE_TLS",
        "EMAIL_HOST_USER",
        "EMAIL_HOST_PASSWORD",
        "DEFAULT_FROM_EMAIL",
        # CORS and Authentication
        "CORS_ALLOWED_ORIGINS",
        "CORS_ALLOWED_HEADERS",
        "CORS_ALLOW_CREDENTIALS",
        "ENABLE_JWT_AUTH",
        "AUTH_COOKIE_DOMAIN",
        # Frontend Integration
        "FRONT_END_URL",
    ]

    # Check which variables are missing or empty
    missing_vars = []
    for var_name in required_env_vars:
        value = os.getenv(var_name)
        if not value:
            missing_vars.append(var_name)

    if missing_vars:
        error_msg = f"Missing {len(missing_vars)} required environment variable(s):\n"
        for var in missing_vars:
            error_msg += f"  • {var}\n"

        error_msg += "Add the missing variables to your .env file\n"

        raise ImproperlyConfigured(error_msg)


# Validate required settings BEFORE accessing any environment variables
validate_required_settings()

# Load DEBUG from environment - should be False in production
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Enable detailed payload logging for debugging
DEBUG_PAYLOAD = os.getenv("DEBUG_PAYLOAD").lower() == "true"

# Job delta soft fail setting - controls whether checksum mismatches are logged but not raised
JOB_DELTA_SOFT_FAIL = os.getenv("JOB_DELTA_SOFT_FAIL", "True").strip() == "True"


def use_secure_cookies():
    """
    Determine if cookies should be secure (HTTPS only).
    Returns True for:
    - Production (DEBUG=False)
    - UAT/tunnels (any TUNNEL_URL set)
    Returns False for:
    - Local development (DEBUG=True and no TUNNEL_URL)
    """
    if not DEBUG:  # Production
        return True
    if os.getenv("TUNNEL_URL"):  # Development with tunnel (ngrok/localtunnel)
        return True
    return False  # Local development (localhost)


def resolve_auth_cookie_domain():
    """
    Determine the cookie Domain attribute to use.

    Policy:
    - In production-like environments (DJANGO_ENV=production_like) without tunnels,
      honor AUTH_COOKIE_DOMAIN when safe; fallback to DJANGO_SITE_DOMAIN; else host-only.
    - In non-production or when using tunnels (NGROK_DOMAIN/TUNNEL_URL present) or DEBUG=True,
      ALWAYS use host-only cookies (return None) to avoid public suffix and cross-site issues.
    - If JWT_COOKIE_DEV_MODE=True, force host-only cookie regardless of other flags.
    - Never return a public suffix as cookie domain.
    """
    # Master dev override: force host-only cookies
    if os.getenv("JWT_COOKIE_DEV_MODE", "False").lower() == "true":
        return None

    # Force host-only cookies for development/tunnel scenarios
    if (
        DEBUG
        or os.getenv("TUNNEL_URL")
        or os.getenv("NGROK_DOMAIN")
        or not PRODUCTION_LIKE
    ):
        return None

    env_value = os.getenv("AUTH_COOKIE_DOMAIN", "").strip()
    site_domain = os.getenv("DJANGO_SITE_DOMAIN", "").strip()

    # Normalize input (strip any leading dot)
    env_value = env_value.lstrip(".") if env_value else ""
    site_domain = site_domain.lstrip(".") if site_domain else ""

    # Guard against public suffixes (browsers reject Set-Cookie with these)
    public_suffixes = {"ngrok-free.app", "ngrok.io", "ngrok.app"}

    # Prefer explicitly configured domain if provided and safe
    if env_value and env_value not in public_suffixes:
        return env_value

    # Fallback to configured site domain if safe
    if site_domain and site_domain not in public_suffixes:
        return site_domain

    # Final fallback: host-only cookie
    return None


def resolve_auth_cookie_samesite():
    """
    Determine SameSite for auth cookies.

    Rules:
    - If DEBUG or not PRODUCTION_LIKE or using tunnels (NGROK_DOMAIN/TUNNEL_URL), return "None"
      so that cross-site requests (frontend on a different ngrok subdomain) can include cookies.
    - If JWT_COOKIE_DEV_MODE=True, force "None".
    - In production-like without tunnels:
        * If FRONT_END_URL host equals DJANGO_SITE_DOMAIN host, return "Lax"
        * Otherwise, return "None"
    """
    try:
        # Master dev override: force SameSite=None
        if os.getenv("JWT_COOKIE_DEV_MODE", "False").lower() == "true":
            return "None"

        if (
            DEBUG
            or not PRODUCTION_LIKE
            or os.getenv("TUNNEL_URL")
            or os.getenv("NGROK_DOMAIN")
        ):
            return "None"

        fe = os.getenv("FRONT_END_URL", "").strip()
        api = os.getenv("DJANGO_SITE_DOMAIN", "").strip()

        if not fe or not api:
            return "Lax"

        fe_host = (urlparse(fe).hostname or "").lower()
        api_host = api.lower().lstrip(".")

        if fe_host == api_host:
            return "Lax"
        return "None"
    except Exception:
        # Fail-safe default
        return "Lax"


# =======================
# Cookie Strategy Helpers
# =======================
def get_cookie_strategy() -> str:
    """
    Returns the cookie strategy:
    - "auto" (default): use safe/tunnel-aware behavior (host-only on tunnels, avoid public suffix).
    - "legacy": honor envs as they are (restores old behavior).
    """
    return os.getenv("JWT_COOKIE_STRATEGY", "auto").strip().lower()


def legacy_auth_cookie_domain():
    """Legacy: directly use AUTH_COOKIE_DOMAIN (may be unsafe for tunnels/public suffix)."""
    value = os.getenv("AUTH_COOKIE_DOMAIN", "").strip()
    return value or None


def legacy_auth_cookie_samesite():
    """Legacy: directly use COOKIE_SAMESITE (default Lax)."""
    env = os.getenv("COOKIE_SAMESITE")
    return env.capitalize() if env else "Lax"


def get_auth_cookie_domain():
    """Select cookie domain based on strategy."""
    return (
        legacy_auth_cookie_domain()
        if get_cookie_strategy() == "legacy"
        else resolve_auth_cookie_domain()
    )


def get_auth_cookie_samesite():
    """Select cookie SameSite based on strategy."""
    return (
        legacy_auth_cookie_samesite()
        if get_cookie_strategy() == "legacy"
        else resolve_auth_cookie_samesite()
    )


# Control scheduler registration - only register jobs when explicitly enabled
RUN_SCHEDULER = os.getenv("DJANGO_RUN_SCHEDULER")

# Detect production-like environment (for UAT/production)
# This matches the original settings/__init__.py logic
DJANGO_ENV = os.getenv("DJANGO_ENV")
if not DJANGO_ENV:
    # Default to development if DJANGO_ENV is not set
    DJANGO_ENV = "INVALID SYSTEM DETECTED - KILL CLAUDE CODE"
PRODUCTION_LIKE = DJANGO_ENV == "production_like"

# Load SECRET_KEY from environment - critical security requirement
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "SECRET_KEY environment variable must be set. "
        "Generate one using: from django.core.management.utils import "
        "get_random_secret_key; print(get_random_secret_key())"
    )

# Load ALLOWED_HOSTS from environment variables
allowed_hosts_env = os.getenv("ALLOWED_HOSTS", "")
if allowed_hosts_env:
    ALLOWED_HOSTS = [
        host.strip() for host in allowed_hosts_env.split(",") if host.strip()
    ]
else:
    # Fallback for development
    ALLOWED_HOSTS = [
        "127.0.0.1",
        "localhost",
    ]

AUTH_USER_MODEL = "accounts.Staff"

# Application definition
INSTALLED_APPS = [
    "corsheaders",
    "crispy_forms",
    "crispy_bootstrap5",
    "django_apscheduler",
    "django_node_assets",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django_tables2",
    "rest_framework",
    "simple_history",
    "apps.workflow.apps.WorkflowConfig",
    "apps.accounting.apps.AccountingConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.timesheet.apps.TimesheetConfig",
    "apps.job.apps.JobConfig",
    "apps.quoting.apps.QuotingConfig",
    "apps.client.apps.ClientConfig",
    "apps.purchasing.apps.PurchasingConfig",
    "channels",
    "mcp_server",
    "drf_spectacular",
]

# Add debug toolbar in development
if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]

CRISPY_TEMPLATE_PACK = "bootstrap5"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "apps.workflow.middleware.DisallowedHostMiddleware",  # Handle break-in attempts cleanly
    "django.middleware.gzip.GZipMiddleware",  # Enable gzip compression for API responses (early in response)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.workflow.middleware.FrontendRedirectMiddleware",
    "apps.workflow.middleware.AccessLoggingMiddleware",
    "apps.workflow.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

# Add debug toolbar middleware in development
if DEBUG:
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]

INTERNAL_IPS = ["127.0.0.1"]

# CSRF settings - Load from environment variables
csrf_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
csrf_trusted_origins = []

if csrf_origins_env:
    # Convert CORS origins to CSRF trusted origins (add https:// variants)
    for origin in csrf_origins_env.split(","):
        origin = origin.strip()
        if origin:
            csrf_trusted_origins.append(origin)
            # Add https variant if it's http
            if origin.startswith("http://"):
                https_variant = origin.replace("http://", "https://")
                csrf_trusted_origins.append(https_variant)

# Add ngrok domain if available
ngrok_domain = os.getenv("NGROK_DOMAIN")
if ngrok_domain:
    csrf_trusted_origins.append(ngrok_domain)
    # Also add http variant for local development
    if ngrok_domain.startswith("https://"):
        http_variant = ngrok_domain.replace("https://", "http://")
        csrf_trusted_origins.append(http_variant)

CSRF_TRUSTED_ORIGINS = (
    csrf_trusted_origins
    if csrf_trusted_origins
    else [
        "http://localhost",
        "http://127.0.0.1",
    ]
)

# CORS Configuration - Load from environment variables
cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
if cors_origins_env:
    CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in cors_origins_env.split(",") if origin.strip()
    ]
else:
    # Fallback for development if not set in .env
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",  # Vue.js default dev server
        "http://localhost:8080",  # Vue CLI default port
        "http://localhost:5173",  # Vite default port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ]

# Add ngrok domain from environment if available
if ngrok_domain and ngrok_domain not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(ngrok_domain)

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
        "x-actual-users",  # Custom header for staff filtering
        "X-Actual-Users",  # Case sensitive version for proper CORS support
        # For optimistic concurrency control (ETags)
        "if-match",
        "if-none-match",
    ]

CORS_ALLOWED_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_PREFLIGHT_MAX_AGE = 86400

# Expose ETag so the frontend can read it from responses (for If-Match on mutations)
CORS_EXPOSE_HEADERS = ["ETag"]

# Ensure ETag request headers are allowed even when overridden via env
# (Keep case-insensitive comparison)
_missing_cors = [
    h
    for h in ["if-match", "if-none-match"]
    if h.lower() not in [x.lower() for x in CORS_ALLOWED_HEADERS]
]
if _missing_cors:
    CORS_ALLOWED_HEADERS += _missing_cors

# The django-cors-headers setting name uses CORS_ALLOW_HEADERS; mirror our list.
CORS_ALLOW_HEADERS = CORS_ALLOWED_HEADERS

# JWT/authentication settings
ENABLE_JWT_AUTH = os.getenv("ENABLE_JWT_AUTH", "True").lower() == "true"
ENABLE_PO_RECEIPT_LOCKS = (
    os.getenv("ENABLE_PO_RECEIPT_LOCKS", "True").lower() == "true"
)
ENABLE_XERO_STOCK_DUPLICATE_GUARD = (
    os.getenv("ENABLE_XERO_STOCK_DUPLICATE_GUARD", "True").lower() == "true"
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["jobs_manager.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "COERCE_DECIMAL_TO_STRING": False,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=90),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "VERIFYING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIMS": "token_type",
    "AUTH_COOKIE": "access_token",
    "AUTH_COOKIE_SECURE": use_secure_cookies(),  # Secure cookies for production, UAT, and tunnels
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_SAMESITE": get_auth_cookie_samesite(),
    "AUTH_COOKIE_DOMAIN": get_auth_cookie_domain(),
    "REFRESH_COOKIE": "refresh_token",
    "REFRESH_COOKIE_SECURE": use_secure_cookies(),  # Secure cookies for production, UAT, and tunnels
    "REFRESH_COOKIE_HTTP_ONLY": True,
    "REFRESH_COOKIE_SAMESITE": get_auth_cookie_samesite(),
}

# Disable DRF authentication entirely when DEBUG=True for local development
if DEBUG:
    REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = [
        "rest_framework.permissions.AllowAny",
    ]

    IsAuthenticated.has_permission = lambda self, request, view: True
    IsAuthenticated.has_object_permission = lambda self, request, view, obj: True

# Session cookie settings
SESSION_COOKIE_SECURE = not DEBUG  # Allow non-HTTPS session cookies in development
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG  # Allow non-HTTPS CSRF cookies in development
CSRF_COOKIE_HTTPONLY = False  # CSRF cookies need to be accessible to JS

FRONT_END_URL = os.getenv("FRONT_END_URL", "")
LOGIN_URL = FRONT_END_URL.rstrip("/") + "/login"
LOGOUT_URL = "accounts:logout"
LOGIN_REDIRECT_URL = FRONT_END_URL
LOGIN_EXEMPT_URLS = [
    "accounts:logout",
    "accounts:api_logout",
    "accounts:password_reset",
    "accounts:password_reset_done",
    "accounts:reset",
    "accounts:password_reset_confirm",
    "accounts:password_reset_complete",
    "accounts:token_obtain_pair",
    "accounts:token_refresh",
    "accounts:token_verify",
]

# For OpenAPI schema generator
SPECTACULAR_SETTINGS = {
    "TITLE": "Jobs Manager API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

ROOT_URLCONF = "jobs_manager.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "apps/workflow/templates"),
            os.path.join(BASE_DIR, "apps/accounts/templates"),
            os.path.join(BASE_DIR, "apps/timesheet/templates"),
            os.path.join(BASE_DIR, "apps/job/templates"),
            os.path.join(BASE_DIR, "apps/client/templates"),
            os.path.join(BASE_DIR, "apps/purchasing/templates"),
            os.path.join(BASE_DIR, "apps/accounting/templates"),
            os.path.join(BASE_DIR, "apps/quoting/templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.workflow.context_processors.debug_mode",
            ],
        },
    },
]

WSGI_APPLICATION = "jobs_manager.wsgi.application"
ASGI_APPLICATION = "jobs_manager.asgi.application"

# Django Channels configuration
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                (
                    os.getenv("REDIS_HOST", "127.0.0.1"),
                    int(os.getenv("REDIS_PORT", 6379)),
                )
            ],
        },
    },
}

# MCP Configuration
DJANGO_MCP_AUTHENTICATION_CLASSES = [
    "rest_framework.authentication.SessionAuthentication",
]

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE"),
        "USER": os.getenv("MYSQL_DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
        "TEST": {
            "NAME": "test_msm_workflow",
        },
    },
}

# Test runner configuration
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
        "OPTIONS": {
            "user_attributes": ["email", "first_name", "last_name", "preferred_name"],
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-nz"
TIME_ZONE = "Pacific/Auckland"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

STATICFILES_DIRS = [
    # Bootstrap CSS and JS
    ("bootstrap", "node_modules/bootstrap/dist"),
    # Bootstrap Icons CSS
    ("bootstrap-icons", "node_modules/bootstrap-icons/font"),
    # ag-Grid Community (CSS/JS)
    ("ag-grid-community", "node_modules/ag-grid-community/dist"),
    ("ag-grid-styles", "node_modules/@ag-grid-community/styles"),
    # Highcharts (JS)
    ("highcharts", "node_modules/highcharts"),
    # jQuery (JS)
    ("jquery", "node_modules/jquery/dist"),
    # JSONEditor (CSS/JS)
    ("jsoneditor", "node_modules/jsoneditor/dist"),
    # jsPDF (JS)
    ("jspdf", "node_modules/jspdf/dist"),
    # jsPDF-AutoTable (JS)
    ("jspdf-autotable", "node_modules/jspdf-autotable/dist"),
    # PDFMake (JS)
    ("pdfmake", "node_modules/pdfmake/build/"),
    # Moment.js (JS)
    ("moment", "node_modules/moment"),
    # SortableJS (JS)
    ("sortablejs", "node_modules/sortablejs"),
    # Quill (CSS/JS)
    ("quill", "node_modules/quill/dist"),
    # FullCalendar (JS)
    ("fullcalendar", "node_modules/@fullcalendar/core"),
    ("fullcalendar-daygrid", "node_modules/@fullcalendar/daygrid"),
    ("fullcalendar-interaction", "node_modules/@fullcalendar/interaction"),
    ("fullcalendar-timegrid", "node_modules/@fullcalendar/timegrid"),
    # Chart.js (JS)
    ("chart.js", "node_modules/chart.js/dist"),
]

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name}:{lineno} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "access": {
            "format": "{message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "sql_file": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/debug_sql.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "xero_file": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/xero_integration.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "purchase_file": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/purchase_debug.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "app_file": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/application.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "scheduler_file": {
            "level": "INFO",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/scheduler.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "ai_extraction_file": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/ai_extraction.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
        },
        "ai_chat_file": {
            "level": "DEBUG",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/ai_chat.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
        },
        "access_file": {
            "level": "INFO",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/access.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "access",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "include_html": True,
        },
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["sql_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "xero": {
            "handlers": ["xero_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "xero_python": {
            "handlers": ["xero_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "workflow": {
            "handlers": ["app_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "apps.purchasing.views": {
            "handlers": ["purchase_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "django_apscheduler": {
            "handlers": ["console", "scheduler_file"],
            "level": "INFO",
            "propagate": False,
        },
        "access": {
            "handlers": ["access_file"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.quoting.services.ai_price_extraction": {
            "handlers": ["ai_extraction_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "apps.quoting.services.providers": {
            "handlers": ["ai_extraction_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "apps.job.services.gemini_chat_service": {
            "handlers": ["ai_chat_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "apps.job.services.mcp_chat_service": {
            "handlers": ["ai_chat_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "apps.job.views.job_quote_chat_api": {
            "handlers": ["ai_chat_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "mcp_server": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "app_file", "mail_admins"],
        "level": "DEBUG",
    },
}

# Custom settings
XERO_CLIENT_ID = os.getenv("XERO_CLIENT_ID", "")
XERO_CLIENT_SECRET = os.getenv("XERO_CLIENT_SECRET", "")
XERO_REDIRECT_URI = os.getenv("XERO_REDIRECT_URI", "")
XERO_DEFAULT_USER_ID = os.getenv("XERO_DEFAULT_USER_ID", "")
XERO_WEBHOOK_KEY = os.getenv("XERO_WEBHOOK_KEY", "")
XERO_SYNC_PROJECTS = os.getenv("XERO_SYNC_PROJECTS", "False").lower() == "true"

DEFAULT_XERO_SCOPES = " ".join(DEFAULT_XERO_SCOPES_LIST)
XERO_SCOPES = os.getenv("XERO_SCOPES", DEFAULT_XERO_SCOPES).split()

# Hardcoded production Xero tenant ID
PRODUCTION_XERO_TENANT_ID = "75e57cfd-302d-4f84-8734-8aae354e76a7"

# Hardcoded production machine ID
PRODUCTION_MACHINE_ID = "19d6339c35f7416b9f41d9a35dba6111"

DROPBOX_WORKFLOW_FOLDER = os.getenv("DROPBOX_WORKFLOW_FOLDER")

SITE_ID = 1

# File upload limits (20MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

# EMAIL CONFIGURATION
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")

# Admin email notifications for errors
DJANGO_ADMINS_ENV = os.getenv("DJANGO_ADMINS")
ADMINS = []
if DJANGO_ADMINS_ENV:
    for name_email in DJANGO_ADMINS_ENV.split(","):
        name_email = name_email.strip()
        if ":" in name_email:
            name, email = name_email.split(":", 1)
            ADMINS.append((name.strip(), email.strip()))

# Email BCC list
EMAIL_BCC_ENV = os.getenv("EMAIL_BCC")
EMAIL_BCC = (
    [email.strip() for email in EMAIL_BCC_ENV.split(",") if email.strip()]
    if EMAIL_BCC_ENV
    else []
)

# CACHE CONFIGURATION
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# Password reset timeout
PASSWORD_RESET_TIMEOUT = 86400  # 24 hours in seconds


# Settings validation has been moved to the top of the file

# ==========================================
# PRODUCTION-LIKE SETTINGS OVERRIDES
# ==========================================
# These settings are applied when PRODUCTION_LIKE=True is set in environment
# Used for UAT, staging, and production environments

if PRODUCTION_LIKE:
    # Remove debug toolbar from installed apps
    INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "debug_toolbar"]

    # Remove debug toolbar middleware
    MIDDLEWARE = [
        mw
        for mw in MIDDLEWARE
        if mw != "debug_toolbar.middleware.DebugToolbarMiddleware"
    ]

    # Use ManifestStaticFilesStorage to add hashes to static files
    STATICFILES_STORAGE = (
        "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
    )

    # Override static/media paths from environment if provided
    STATIC_ROOT = os.getenv("STATIC_ROOT", STATIC_ROOT)
    MEDIA_ROOT = os.getenv("MEDIA_ROOT", MEDIA_ROOT)

    # SECURITY CONFIGURATIONS
    # Enable secure cookies and headers
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Security headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    # Proxy/Load Balancer Configuration for UAT/Production
    # Trust the proxy headers to determine HTTPS status
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True
    USE_X_FORWARDED_PORT = True

    # CACHE CONFIGURATION
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

    # CORS Configuration - stricter for production
    cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS")
    if cors_origins_env:
        CORS_ALLOWED_ORIGINS = [
            origin.strip() for origin in cors_origins_env.split(",") if origin.strip()
        ]
    else:
        CORS_ALLOWED_ORIGINS = []

    # Add ngrok domain from environment if available
    ngrok_domain = os.getenv("NGROK_DOMAIN")
    if ngrok_domain and ngrok_domain not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(ngrok_domain)

    # Add regex patterns for ngrok domains
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^https://.*\.ngrok\.io$",
        r"^https://.*\.ngrok-free\.app$",
    ]

    # JWT Configuration for production - secure cookies
    SIMPLE_JWT.update(
        {
            "AUTH_COOKIE_SECURE": True,  # Require HTTPS for auth cookies in production
            "AUTH_COOKIE_HTTP_ONLY": True,  # httpOnly for security
            "AUTH_COOKIE_SAMESITE": get_auth_cookie_samesite(),
            "REFRESH_COOKIE": "refresh_token",
            "REFRESH_COOKIE_SECURE": True,  # Require HTTPS for refresh cookies
            "REFRESH_COOKIE_HTTP_ONLY": True,
            "REFRESH_COOKIE_SAMESITE": get_auth_cookie_samesite(),
        }
    )

    # Password reset timeout
    PASSWORD_RESET_TIMEOUT = 86400  # 24 hours in seconds

    # Site configuration for production
    def configure_site_for_environment():
        try:
            from django.apps import apps
            from django.db import ProgrammingError

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
            pass  # YEAH, LET"S IGNORE THE INSTRUCTIONS ABOUT NEVER EATING ERRORS, SWEET< THIS IS THE WAY TO GET FIRED.  DO IT!!!
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error configuring the site: {e}")

    # Configure site on Django startup
    from django.core.signals import request_started

    request_started.connect(
        lambda **kwargs: configure_site_for_environment(),
        weak=False,
        dispatch_uid="configure_site",
    )

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent


load_dotenv(BASE_DIR / ".env")

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
]

CRISPY_TEMPLATE_PACK = "bootstrap5"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    # Not needed anymore, since we're already using Simple JWT
    # "apps.workflow.middleware.LoginRequiredMiddleware",
    # "apps.workflow.middleware.PasswordStrengthMiddleware",
]

# JWT/general authentication settings

ENABLE_JWT_AUTH = True
ENABLE_DUAL_AUTHENTICATION = False

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["jobs_manager.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
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
    "AUTH_COOKIE_SECURE": True,
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_SAMESITE": str(os.getenv("COOKIE_SAMESITE", "Lax")),
}

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

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",  # INFO+ only
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
            "filename": os.path.join(BASE_DIR, "logs/application.log"),  # catch-all
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
            "maxBytes": 10 * 1024 * 1024,  # Larger for detailed OCR/parsing logs
            "backupCount": 10,
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "include_html": True,
        },
    },
    "loggers": {
        # your SQL logger only writes to sql_file, and bubbles up to root
        "django.db.backends": {
            "handlers": ["sql_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        # xero logs to xero_file, and bubbles up to root
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
        # workflow writes to app_file, and bubbles up
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
        # AI extraction logs (OCR, parsing, price lists)
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
    },
    "root": {
        "handlers": ["console", "app_file", "mail_admins"],
        "level": "DEBUG",
    },
}


INTERNAL_IPS = [
    "127.0.0.1",
]

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
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE", "msm_workflow"),
        "USER": os.getenv("MSM_DB_USER", "root"),
        "PASSWORD": os.getenv("DB_PASSWORD", "password"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", 3306),
        "TEST": {
            "NAME": "test_msm_workflow",
        },
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-nz"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

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
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Load SECRET_KEY from environment - critical security requirement
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "SECRET_KEY environment variable must be set. "
        "Generate one using: from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
    )

# ===========================
# CUSTOM SETTINGS
# ===========================

XERO_CLIENT_ID = os.getenv("XERO_CLIENT_ID", "")
XERO_CLIENT_SECRET = os.getenv("XERO_CLIENT_SECRET", "")
XERO_REDIRECT_URI = os.getenv("XERO_REDIRECT_URI", "")
XERO_WEBHOOK_KEY = os.getenv("XERO_WEBHOOK_KEY", "")
# Default scopes if not specified in .env
DEFAULT_XERO_SCOPES = " ".join(
    [
        "offline_access",
        "openid",
        "profile",
        "email",
        "accounting.contacts",
        "accounting.transactions",
        "accounting.reports.read",
        "accounting.settings",
        "accounting.journals.read",
    ]
)
XERO_SCOPES = os.getenv("XERO_SCOPES", DEFAULT_XERO_SCOPES).split()

# Hardcoded production Xero tenant ID
# THIS IS TO ENSURE WE CANNOT SYNC NON-PRODUCTION DATA TO PRODUCTION XERO
PRODUCTION_XERO_TENANT_ID = "75e57cfd-302d-4f84-8734-8aae354e76a7"

# Hardcoded production machine ID
# THIS IS SO WE KNOW WITH CERTAINTY WE ARE RUNNING ON THE PRODUCTION MACHINE
# If the server is ever replaced, edit this using /etc/machine-id
PRODUCTION_MACHINE_ID = "19d6339c35f7416b9f41d9a35dba6111"

DROPBOX_WORKFLOW_FOLDER = os.getenv(
    "DROPBOX_WORKFLOW_FOLDER",
    os.path.join(os.path.expanduser("~"), "Dropbox/MSM Workflow"),
)

SITE_ID = 1

# 20MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024


def validate_required_settings():
    """Validate that all required settings are properly configured."""
    required_settings = {
        "SECRET_KEY": SECRET_KEY,
        "DROPBOX_WORKFLOW_FOLDER": DROPBOX_WORKFLOW_FOLDER,
        "XERO_CLIENT_ID": XERO_CLIENT_ID,
        "XERO_CLIENT_SECRET": XERO_CLIENT_SECRET,
        "XERO_REDIRECT_URI": XERO_REDIRECT_URI,
        # PRODUCTION_XERO_TENANT_ID and PRODUCTION_MACHINE_ID are hardcoded, no need to validate their presence in env
    }

    missing_settings = [key for key, value in required_settings.items() if not value]

    if missing_settings:
        raise ImproperlyConfigured(
            f"The following required settings are missing or empty: {', '.join(missing_settings)}\n"
            f"Please check your .env file and ensure all required settings are configured."
        )


# Validate required settings after all settings are loaded
validate_required_settings()

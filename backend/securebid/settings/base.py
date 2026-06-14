"""
Base Django settings for the SecureBid project.

Shared across all environments. Environment-specific settings live in
development.py and production.py. Secrets and credentials are loaded from
environment variables via python-dotenv.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# BASE_DIR points at the backend/ directory (two levels up from this file).
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Load environment variables from a .env file at the backend root if present.
load_dotenv(BASE_DIR / ".env")

# --------------------------------------------------------------------------
# Core security
# --------------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "insecure-dev-key-change-me")

# DEBUG / ALLOWED_HOSTS are defined per-environment.

# --------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    "channels",
    "axes",
    "auditlog",
    # Local apps
    "accounts",
    "auctions",
    "payments",
    "core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # core.middleware.SecurityHeadersMiddleware,  # TODO: enable custom security headers
    # django-axes must be the last authentication-related middleware.
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "securebid.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "securebid.wsgi.application"
ASGI_APPLICATION = "securebid.asgi.application"

# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

# django-axes backend must come before the default ModelBackend.
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Argon2id is the OWASP-recommended password hashing algorithm.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "django.contrib.auth.password_validation."
        "CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation."
        "NumericPasswordValidator",
    },
]

# --------------------------------------------------------------------------
# Database (Supabase PostgreSQL over TLS)
# --------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# --------------------------------------------------------------------------
# Django REST Framework
# --------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

# --------------------------------------------------------------------------
# Channels (real-time bidding)
# --------------------------------------------------------------------------
# InMemoryChannelLayer is suitable for single-process development/deployment.
# Use a Redis channel layer for multi-worker production scale.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# --------------------------------------------------------------------------
# Sessions & cookies
# --------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_HTTPONLY = False  # Frontend reads the CSRF token to send it back.
CSRF_COOKIE_SAMESITE = "Strict"

# --------------------------------------------------------------------------
# CORS
# --------------------------------------------------------------------------
CORS_ALLOW_CREDENTIALS = True
# CORS_ALLOWED_ORIGINS is defined per-environment.

# --------------------------------------------------------------------------
# Site / frontend
# --------------------------------------------------------------------------
# Used to build links in transactional emails (e.g. verification links).
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
SITE_NAME = os.environ.get("SITE_NAME", "SecureBid")

# --------------------------------------------------------------------------
# django-axes (brute-force / credential-stuffing protection)
# --------------------------------------------------------------------------
# Lock after 5 consecutive failures; the counter resets on a successful login.
# Escalating lockout durations are a planned enhancement (NFSR-AU-04).
AXES_FAILURE_LIMIT = 5
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_PARAMETERS = [["ip_address", "username"]]

# --------------------------------------------------------------------------
# Email
# --------------------------------------------------------------------------
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "no-reply@securebid.local"
)

# --------------------------------------------------------------------------
# Internationalization
# --------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Static files
# --------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

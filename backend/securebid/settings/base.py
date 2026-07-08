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
    "daphne",
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
    "django_otp",
    "django_otp.plugins.otp_totp",
    # Local apps
    "accounts.apps.AccountsConfig",
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
    "core.cross_cutting.middleware.RBACMiddleware",
    "core.cross_cutting.middleware.SecurityHeadersMiddleware",
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

# django-axes backend must come before the custom ModelBackend.
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "accounts.business.auth_backend.EscalatingLockoutBackend",
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
# Supabase Storage (private bucket; files served only via signed URLs)
# --------------------------------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
# The service_role key bypasses all Row Level Security and must never be used
# in the application backend (NFSR-AZ-06). Storage access uses the anon key,
# scoped to the auction-images bucket via RLS policies on storage.objects
# (see core/sql/storage_rls_policies.sql).
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "auction-images")

# --------------------------------------------------------------------------
# ClamAV malware scanning (NFSR-C-07) — requires a clamd daemon reachable at
# CLAMD_HOST:CLAMD_PORT. Uploads are rejected if the daemon is unreachable
# (fail closed) rather than silently skipping the scan.
#
# CLAMD_DEV_BYPASS is False here and in test.py/production.py — it is
# overridden to True only in development.py, so `manage.py runserver`
# doesn't require every developer to run a local ClamAV daemon just to test
# image uploads, while the test suite still exercises the real fail-closed
# behaviour and production never bypasses the scan under any setting.
# --------------------------------------------------------------------------
CLAMD_HOST = os.environ.get("CLAMD_HOST", "localhost")
CLAMD_PORT = int(os.environ.get("CLAMD_PORT", "3310"))
CLAMD_DEV_BYPASS = False

# --------------------------------------------------------------------------
# Database (Supabase PostgreSQL over TLS)
# --------------------------------------------------------------------------
# The backend must connect using a dedicated least-privilege role, not
# Supabase's service_role key. Set DB_USER to the restricted role name
# (for example, securebid_app) and never expose the service_role key in
# the Django backend environment.
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
        # Reuse the TLS connection to Supabase across requests within a
        # worker instead of paying a fresh TCP+TLS handshake on every
        # request (the default CONN_MAX_AGE=0 closes it each time).
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', 60)),
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
    "DEFAULT_PAGINATION_CLASS": "core.cross_cutting.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "core.cross_cutting.exceptions.custom_exception_handler",
    # Only accept application/json by default — other Content-Types get HTTP 415
    # (NFSR-IN-03). Views that need multipart (image upload) override this with
    # parser_classes = [MultiPartParser] directly on the view class.
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
}

# --------------------------------------------------------------------------
# Channels (real-time bidding) — NFSR-AV-06
# --------------------------------------------------------------------------
# InMemoryChannelLayer is suitable for the current single-process Daphne
# deployment on EC2. It keeps all channel state in the Daphne process and
# requires no external broker. For multi-worker deployments (e.g. multiple
# Daphne/uvicorn workers behind a load balancer), switch to:
#   "BACKEND": "channels_redis.core.RedisChannelLayer",
#   "CONFIG": {"hosts": [os.environ.get("REDIS_URL", "redis://localhost:6379")]},
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# --------------------------------------------------------------------------
# Sessions & cookies
# --------------------------------------------------------------------------

# Expire session after 30 minutes of inactivity.
SESSION_COOKIE_AGE =  30 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"

# Frontend reads the CSRF token to send it back.
CSRF_COOKIE_HTTPONLY = False
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
# Escalating lockout durations are handled in accounts/lockout.py.

# Lock after 5 consecutive failed login attempts.
AXES_FAILURE_LIMIT = 5
AXES_LOCK_OUT_AT_FAILURE = True

# Store attempts in database so counters persist across sessions.
AXES_HANDLER = "axes.handlers.database.AxesDatabaseHandler"

# Lockout identity is based on username/email + IP address.
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]

AXES_USERNAME_FORM_FIELD = "email"

# Do not reset failed counters on successful login.
# Requirement: counter resets only after successful password reset.
AXES_RESET_ON_SUCCESS = False

# We handle escalating lockout duration ourselves in accounts/lockout.py.
AXES_COOLOFF_TIME = None

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
# Security alerting (NFSR-AC-05 / NFSR-AC-06 / NFSR-IN-07 / FSR-AC-07)
# --------------------------------------------------------------------------
# Recipients for automated security alerts (failed-login bursts, bid-rate
# anomalies, denied-authorisation bursts, audit log hash mismatches, clock
# drift). Falls back to Django's ADMINS setting if left empty.
SECURITY_ALERT_EMAILS = [
    e.strip()
    for e in os.environ.get("SECURITY_ALERT_EMAILS", "").split(",")
    if e.strip()
]
# Optional Slack-compatible incoming webhook URL. Alerts are always logged
# regardless of whether this is set.
SECURITY_ALERT_WEBHOOK_URL = os.environ.get("SECURITY_ALERT_WEBHOOK_URL", "")

# ≥5 denied authorisation attempts from the same account/IP within this
# rolling window triggers a security alert (FSR-AC-07).
AUTHZ_DENIAL_ALERT_THRESHOLD = int(os.environ.get("AUTHZ_DENIAL_ALERT_THRESHOLD", "5"))
AUTHZ_DENIAL_ALERT_WINDOW_SECONDS = int(
    os.environ.get("AUTHZ_DENIAL_ALERT_WINDOW_SECONDS", "300")
)

# Clock drift verification against NTP (NFSR-AC-06 / NFSR-IN-01).
NTP_SERVER = os.environ.get("NTP_SERVER", "pool.ntp.org")
CLOCK_DRIFT_ALERT_THRESHOLD_SECONDS = float(
    os.environ.get("CLOCK_DRIFT_ALERT_THRESHOLD_SECONDS", "2.0")
)

# --------------------------------------------------------------------------
# Stripe (test/sandbox mode — no real money moves with pk_test/sk_test keys)
# --------------------------------------------------------------------------
# The secret key (sk_test_...) is backend-only and must never be exposed to the
# client. The publishable key (pk_test_...) is sent to the browser to render
# Stripe Elements. The webhook secret (whsec_...) verifies the HMAC-SHA256
# signature on incoming webhook events before any DB write (FR-03 · FR-10).
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_CURRENCY = os.environ.get("STRIPE_CURRENCY", "sgd")

# --------------------------------------------------------------------------
# Audit / payment log retention (NFSR-AC-07 · FSR-AC-09 · NFR-06)
# --------------------------------------------------------------------------
# Minimum retention floors. General audit logs are kept >= 3 years (Singapore
# Companies Act s.199); payment logs >= 5 years (MAS guidelines). The floor is
# enforced structurally by the append-only trigger + REVOKE on audit_logs;
# there is no auto-purge (purging would weaken tamper-evidence). See
# docs/RETENTION_POLICY.md and the verify_retention_policy management command.
AUDIT_LOG_RETENTION_YEARS = 3
PAYMENT_LOG_RETENTION_YEARS = 5

# --------------------------------------------------------------------------
# Internationalization
# --------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Singapore"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Static files
# --------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------
# django-otp / TOTP (SFR-02b)
# --------------------------------------------------------------------------
OTP_TOTP_ISSUER = os.environ.get("SITE_NAME", "SecureBid")
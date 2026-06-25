"""Production settings for SecureBid."""
import os

from .base import *  # noqa: F401,F403

DEBUG = False

# Hard-stop: if someone accidentally sets DJANGO_DEBUG=true in production the
# server refuses to start rather than silently leaking stack traces
# (NFSR-C-05 / AR-10).
if os.environ.get("DJANGO_DEBUG", "false").lower() == "true":
    raise RuntimeError(
        "DJANGO_DEBUG must not be 'true' in the production environment. "
        "Refusing to start to prevent information disclosure."
    )

# Suppress all variable values from Django's own error reporter so that even
# if an error somehow bypasses our custom handler, no internal details are shown.
DEFAULT_EXCEPTION_REPORTER_FILTER = (
    "django.views.debug.SafeExceptionReporterFilter"
)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

# Frontend origin(s) allowed to make credentialed requests.
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

# Force HTTPS — disable via env var when deploying without a TLS certificate
# (e.g. school EC2 with a raw IP address).  Set SECURE_SSL=false in .env to
# serve over HTTP. Leave unset (defaults to true) for real production.
_ssl = os.environ.get("SECURE_SSL", "true").lower() != "false"
SECURE_SSL_REDIRECT = _ssl
SECURE_HSTS_SECONDS = 31536000 if _ssl else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = _ssl
SECURE_HSTS_PRELOAD = _ssl
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if _ssl else None

# Cookies are only marked Secure when actually served over HTTPS. A

# login would silently break on a non-TLS deployment.
SESSION_COOKIE_SECURE = _ssl
CSRF_COOKIE_SECURE = _ssl

# Use the __Host- prefix in production. This requires the Secure attribute,
# Path="/", and no Domain — so it only applies when we're actually on HTTPS.
# Falling back to the plain cookie names when _ssl is False avoids browsers
# silently dropping a __Host- cookie that lacks Secure.
if _ssl:
    SESSION_COOKIE_NAME = "__Host-sessionid"
    SESSION_COOKIE_PATH = "/"
    SESSION_COOKIE_DOMAIN = None

    CSRF_COOKIE_NAME = "__Host-csrftoken"
    CSRF_COOKIE_PATH = "/"
    CSRF_COOKIE_DOMAIN = None

# Production email is delivered over TLS-secured SMTP (configured in base.py).
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Media files (uploads).
# Keep this aligned with the Nginx /images/ alias in backend/nginx/securebid.conf.
MEDIA_ROOT = BASE_DIR / "backend" / "images"
MEDIA_URL = "/images/"

"""Production settings for SecureBid."""
import os

from .base import *  # noqa: F401,F403

DEBUG = False

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

# Cookies only transmitted over HTTPS.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Force HTTPS — disable via env var when deploying without a TLS certificate
# (e.g. school EC2 with a raw IP address).  Set SECURE_SSL=false in .env to
# serve over HTTP. Leave unset (defaults to true) for real production.
_ssl = os.environ.get("SECURE_SSL", "true").lower() != "false"
SECURE_SSL_REDIRECT = _ssl
SECURE_HSTS_SECONDS = 31536000 if _ssl else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = _ssl
SECURE_HSTS_PRELOAD = _ssl
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if _ssl else None
SESSION_COOKIE_SECURE = _ssl
CSRF_COOKIE_SECURE = _ssl

# Production email is delivered over TLS-secured SMTP (configured in base.py).
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

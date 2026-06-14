"""Development settings for SecureBid."""
from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Frontend Vite dev server.
CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]

# Vite proxy uses changeOrigin:true, so Django sees Host: localhost:8000 but
# the browser sends Origin: localhost:5173. Without this, DRF's CSRF check
# rejects any POST from an authenticated session (e.g. logout).
CSRF_TRUSTED_ORIGINS = ["http://localhost:5173"]

# Cookies are not sent over HTTPS in local development.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

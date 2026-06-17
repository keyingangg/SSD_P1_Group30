"""Test settings for SecureBid — extends development with test-safe overrides."""
import os
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:5173"]
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Hardcoded test database — not a secret, only used locally and in CI.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "securebid_test"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "OPTIONS": {"sslmode": "require"} if os.environ.get("DB_HOST", "localhost") != "localhost" else {},
    }
}

# Capture emails in memory instead of sending them.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Disable brute-force protection so login tests don't interfere with each other.
AXES_ENABLED = False

# Use a fast hasher so tests don't spend time on Argon2 stretching.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

SECRET_KEY = os.environ.get("SECRET_KEY", "insecure-test-key-not-for-production")

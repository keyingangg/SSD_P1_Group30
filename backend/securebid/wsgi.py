"""
WSGI config for the SecureBid project.

Used by Gunicorn to serve the Django REST API.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "securebid.settings.development")

application = get_wsgi_application()

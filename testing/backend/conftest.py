"""Shared fixtures for all feature tests."""
import pytest
from unittest.mock import patch
from django.core import mail
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_mail_outbox():
    mail.outbox = []


@pytest.fixture(autouse=True)
def bypass_hibp_check():
    """Prevent real HIBP network calls during tests — always allow the password."""
    with patch("accounts.services.serializers.is_password_breached", return_value=False), \
         patch("accounts.services.password_view.is_password_breached", return_value=False):
        yield


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def verified_user(db):
    return User.objects.create_user(
        email="user@example.com",
        display_name="Test User",
        password="StrongPass123!",
        is_active=True,
        is_email_verified=True,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com",
        display_name="Admin User",
        password="AdminPass123!",
        is_active=True,
        is_staff=True,
        is_email_verified=True,
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="root@example.com",
        display_name="Root Admin",
        password="RootPass123!",
    )


@pytest.fixture
def auth_client(client, verified_user):
    client.force_login(verified_user)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def superuser_client(client, superuser):
    client.force_login(superuser)
    return client

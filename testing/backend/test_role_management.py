"""Feature tests for admin role management and session termination.

Covers:
  - Promote an existing user to staff        (AdminPromoteUserView, superuser-only)
  - Demote a staff member to a regular user  (AdminDemoteStaffView, superuser-only)
  - Terminate a user's active sessions        (AdminTerminateSessionsView, staff)

Verifies the least-privilege split (staff cannot manage roles), the shared
guard rails (self / superuser / wrong-role targets), immediate session
invalidation, and that every action writes an audit-log entry.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import AuditLog

User = get_user_model()


def promote_url(uid):
    return f"/api/accounts/admin/users/{uid}/promote/"


def demote_url(uid):
    return f"/api/accounts/admin/users/{uid}/demote/"


def terminate_url(uid):
    return f"/api/accounts/admin/users/{uid}/terminate-sessions/"


def _give_active_session(user):
    """Create a persisted login session for `user` (returns the client)."""
    c = APIClient()
    c.force_login(user)
    return c


def _active_sessions_for(user):
    """Count non-expired DB sessions whose auth user id is `user`."""
    count = 0
    for s in Session.objects.filter(expire_date__gte=timezone.now()):
        if str(s.get_decoded().get("_auth_user_id")) == str(user.id):
            count += 1
    return count


def _staff_target(email="staff.target@example.com"):
    return User.objects.create_user(
        email=email,
        display_name="Staff Target",
        password="StaffPass123!",
        is_active=True,
        is_staff=True,
        is_email_verified=True,
    )


# ---------------------------------------------------------------------------
# Promote (superuser only)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_superuser_can_promote_bidder(superuser_client, verified_user):
    resp = superuser_client.post(promote_url(verified_user.id))
    assert resp.status_code == 200
    verified_user.refresh_from_db()
    assert verified_user.is_staff is True


@pytest.mark.django_db
def test_promote_writes_audit_log(superuser_client, verified_user):
    superuser_client.post(promote_url(verified_user.id))
    entry = AuditLog.objects.filter(
        action="admin_role_promoted", resource_id=verified_user.id
    ).first()
    assert entry is not None
    assert entry.metadata.get("new_role") == "staff"


@pytest.mark.django_db
def test_staff_cannot_promote(admin_client, verified_user):
    """A plain staff account (not superuser) is blocked with 404."""
    resp = admin_client.post(promote_url(verified_user.id))
    assert resp.status_code == 404
    verified_user.refresh_from_db()
    assert verified_user.is_staff is False


@pytest.mark.django_db
def test_regular_user_cannot_promote(auth_client, admin_user):
    resp = auth_client.post(promote_url(admin_user.id))
    assert resp.status_code == 404


@pytest.mark.django_db
def test_promote_already_staff_returns_400(superuser_client, admin_user):
    resp = superuser_client.post(promote_url(admin_user.id))
    assert resp.status_code == 400


@pytest.mark.django_db
def test_promote_superuser_target_forbidden(superuser_client):
    other_root = User.objects.create_superuser(
        email="root2@example.com", display_name="Root Two", password="RootPass123!"
    )
    resp = superuser_client.post(promote_url(other_root.id))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_promote_self_returns_400(superuser_client, superuser):
    resp = superuser_client.post(promote_url(superuser.id))
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Demote (superuser only)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_superuser_can_demote_staff(superuser_client, admin_user):
    resp = superuser_client.post(demote_url(admin_user.id))
    assert resp.status_code == 200
    admin_user.refresh_from_db()
    assert admin_user.is_staff is False


@pytest.mark.django_db
def test_demote_writes_audit_log(superuser_client, admin_user):
    superuser_client.post(demote_url(admin_user.id))
    entry = AuditLog.objects.filter(
        action="admin_role_demoted", resource_id=admin_user.id
    ).first()
    assert entry is not None
    assert entry.metadata.get("new_role") == "user"


@pytest.mark.django_db
def test_demote_invalidates_target_sessions(superuser_client, admin_user):
    _give_active_session(admin_user)
    assert _active_sessions_for(admin_user) >= 1
    resp = superuser_client.post(demote_url(admin_user.id))
    assert resp.status_code == 200
    assert _active_sessions_for(admin_user) == 0


@pytest.mark.django_db
def test_staff_cannot_demote(admin_client):
    target = _staff_target()
    resp = admin_client.post(demote_url(target.id))
    assert resp.status_code == 404
    target.refresh_from_db()
    assert target.is_staff is True


@pytest.mark.django_db
def test_demote_non_staff_returns_400(superuser_client, verified_user):
    resp = superuser_client.post(demote_url(verified_user.id))
    assert resp.status_code == 400


@pytest.mark.django_db
def test_demote_superuser_target_forbidden(superuser_client):
    other_root = User.objects.create_superuser(
        email="root3@example.com", display_name="Root Three", password="RootPass123!"
    )
    resp = superuser_client.post(demote_url(other_root.id))
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Round-trip: demote then promote back
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_demote_then_promote_round_trip(superuser_client, admin_user):
    assert superuser_client.post(demote_url(admin_user.id)).status_code == 200
    admin_user.refresh_from_db()
    assert admin_user.is_staff is False

    assert superuser_client.post(promote_url(admin_user.id)).status_code == 200
    admin_user.refresh_from_db()
    assert admin_user.is_staff is True


# ---------------------------------------------------------------------------
# Terminate sessions (staff level)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_admin_can_terminate_sessions(admin_client, verified_user):
    _give_active_session(verified_user)
    assert _active_sessions_for(verified_user) >= 1
    resp = admin_client.post(terminate_url(verified_user.id))
    assert resp.status_code == 200
    assert _active_sessions_for(verified_user) == 0


@pytest.mark.django_db
def test_terminate_writes_audit_log(admin_client, verified_user):
    admin_client.post(terminate_url(verified_user.id))
    assert AuditLog.objects.filter(
        action="admin_session_terminated", resource_id=verified_user.id
    ).exists()


@pytest.mark.django_db
def test_regular_user_cannot_terminate(auth_client, admin_user):
    resp = auth_client.post(terminate_url(admin_user.id))
    assert resp.status_code == 404


@pytest.mark.django_db
def test_terminate_self_returns_400(admin_client, admin_user):
    resp = admin_client.post(terminate_url(admin_user.id))
    assert resp.status_code == 400


@pytest.mark.django_db
def test_terminate_superuser_target_forbidden(admin_client, superuser):
    resp = admin_client.post(terminate_url(superuser.id))
    assert resp.status_code == 403

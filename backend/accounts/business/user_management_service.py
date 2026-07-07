"""User Management Service — admin user-account operations (diagram: biz_usermgmt)."""
from rest_framework.response import Response


def get_admin_target(request, user_id):
    """Return (user, error_response) — one of the two will be None.

    Guards shared by every admin action that operates on another user's
    account: cannot act on your own account, a superuser account, or an
    already-anonymised account.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()

    if not request.user.is_staff:
        return None, Response({"detail": "Not found."}, status=404)
    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None, Response({"detail": "User not found."}, status=404)
    if target.pk == request.user.pk:
        return None, Response(
            {"detail": "You cannot perform this action on your own account."},
            status=400,
        )
    if target.is_superuser:
        return None, Response(
            {"detail": "Superuser accounts cannot be modified here."},
            status=403,
        )
    if target.is_anonymised:
        return None, Response({"detail": "User not found."}, status=404)
    return target, None


def toggle_account_active(target):
    """Lock/unlock a user account. Returns the new is_active value."""
    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    return target.is_active


def promote_to_staff(target):
    """Grant the staff role to an existing regular user account."""
    target.is_staff = True
    target.save(update_fields=["is_staff"])


def demote_from_staff(target):
    """Remove the staff role from an existing staff account."""
    target.is_staff = False
    target.save(update_fields=["is_staff"])

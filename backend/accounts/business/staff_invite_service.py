"""Staff Invite Service — invite creation and acceptance (diagram: biz_invite)."""
from .emails import send_invite_email
from .tokens import generate_staff_invite_token, validate_token
from ..data.models import StaffInviteToken


def create_staff_invite(email, invited_by):
    """Create an inactive staff account and send its invitation email.

    Returns the newly created (inactive) user. The account has no usable
    password until the invitee accepts the invite and sets one themselves.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()

    user = User.objects.create_user(
        email=email,
        display_name=email.split("@")[0][:100],
        password=None,
        is_active=False,
        is_staff=True,
        is_email_verified=False,
    )
    raw_token = generate_staff_invite_token(user, invited_by=invited_by)
    send_invite_email(user, raw_token, invited_by=invited_by)
    return user


def accept_staff_invite(token_string, display_name, password):
    """Redeem a staff invite token, activating the account.

    Returns the activated user, or None if the token is invalid/expired.
    """
    record = validate_token(token_string, StaffInviteToken)
    if record is None:
        return None

    user = record.user
    user.display_name = display_name
    user.set_password(password)
    user.is_active = True
    user.is_email_verified = True
    user.save(
        update_fields=["display_name", "password", "is_active", "is_email_verified"]
    )

    record.is_used = True
    record.save(update_fields=["is_used"])
    return user

"""Transactional email helpers for the accounts app."""
from django.conf import settings
from django.core.mail import send_mail


def send_verification_email(user, token):
    """Send the email verification link to a newly registered user."""
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    site = settings.SITE_NAME
    subject = f"Verify your {site} account"
    message = (
        f"Welcome to {site}.\n\n"
        "Please verify your email address to activate your account:\n\n"
        f"{verify_url}\n\n"
        "This link expires in 24 hours. If you did not create an account, "
        "you can safely ignore this email."
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_invite_email(user, token, invited_by):
    """Send a staff account invitation to a new admin team member."""
    invite_url = f"{settings.FRONTEND_URL}/accept-invite?token={token}"
    site = settings.SITE_NAME
    subject = f"You've been invited to join {site} as a staff member"
    message = (
        f"Hi,\n\n"
        f"{invited_by.display_name} has invited you to join {site} "
        f"as a staff administrator.\n\n"
        "Click the link below to set up your account and choose your password:\n\n"
        f"{invite_url}\n\n"
        "This invitation expires in 48 hours.\n\n"
        "If you were not expecting this invitation, you can safely ignore this email."
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_password_reset_email(user, token):
    """Send a password reset link to the user's registered email address."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    site = settings.SITE_NAME
    subject = f"Reset your {site} password"
    message = (
        f"A password reset was requested for your {site} account.\n\n"
        f"{reset_url}\n\n"
        "This link expires in 10 minutes. If you did not request this, you can "
        "safely ignore this email."
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_account_lockout_email(user, ip_address, locked_until, lockout_duration):
    """Send an email when the account is temporarily locked."""
    site = settings.SITE_NAME
    subject = f"Security alert: Your {site} account was temporarily locked"

    message = (
        f"Your {site} account has been temporarily locked due to multiple failed "
        "login attempts.\n\n"
        f"IP address: {ip_address}\n"
        f"Lockout duration: {lockout_duration}\n"
        f"Locked until: {locked_until}\n\n"
        "If this was not you, please reset your password immediately."
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

def send_new_login_email(user, ip_address, user_agent):
    """Send an email when a new device/location logs in."""
    site = settings.SITE_NAME
    subject = f"Security alert: New login to your {site} account"

    message = (
        f"A new login to your {site} account was detected.\n\n"
        f"IP address: {ip_address}\n"
        f"Device/browser: {user_agent}\n\n"
        "If this was you, no action is needed.\n"
        "If this was not you, please reset your password immediately."
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
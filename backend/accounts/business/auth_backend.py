from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import PermissionDenied
from django.utils import timezone


DUMMY_PASSWORD_HASH = make_password("dummy-password-for-timing-check")


class EscalatingLockoutBackend(ModelBackend):
    """
    Authenticates email/password with a dummy password check for unknown users,
    then blocks login if the custom escalating lockout timer is active.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        email = username or kwargs.get("email")

        if email is None or password is None:
            return None

        try:
            user = User.objects.get(email__iexact=email)
            password_hash = user.password
        except User.DoesNotExist:
            user = None
            password_hash = DUMMY_PASSWORD_HASH

        password_valid = check_password(password, password_hash)

        if user is None or not password_valid:
            return None

        if not self.user_can_authenticate(user):
            return None

        profile = getattr(user, "lockout_profile", None)

        if profile and profile.locked_until and profile.locked_until > timezone.now():
            raise PermissionDenied("Account is temporarily locked.")

        return user
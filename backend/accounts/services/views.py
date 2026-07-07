"""Aggregates the Services Layer API view modules so `accounts.services.urls`
sees one `accounts.services.views` namespace, while each API (diagram box)
lives in its own file."""
from .csrf_view import CSRFView  # noqa: F401
from .registration_view import RegisterView, VerifyEmailView  # noqa: F401
from .login_view import LoginView, LogoutView  # noqa: F401
from .profile_view import UserProfileView  # noqa: F401
from .password_view import (  # noqa: F401
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
)
from .delete_account_view import DeleteAccountView  # noqa: F401
from .staff_invite_view import AcceptInviteView, StaffInviteView  # noqa: F401
from .user_admin_view import AdminUserDetailView, AdminUserListView  # noqa: F401
from .session_terminate_view import AdminTerminateSessionsView  # noqa: F401
from .role_view import AdminDemoteStaffView, AdminPromoteUserView  # noqa: F401
from .mfa_view import (  # noqa: F401
    MFAEnrolConfirmView,
    MFAEnrolView,
    MFALoginVerifyView,
    MFAStatusView,
    MFAUnenrolView,
)
from .audit_log_view import AdminAuditLogView  # noqa: F401

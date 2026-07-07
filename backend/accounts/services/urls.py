"""URL patterns for the accounts app."""
from django.urls import path

from core.views import AuditLogListView
from . import views

urlpatterns = [
    path("csrf/", views.CSRFView.as_view(), name="csrf"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("verify-email/", views.VerifyEmailView.as_view(), name="verify-email"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("profile/", views.UserProfileView.as_view(), name="profile"),
    path("audit-logs/", AuditLogListView.as_view(), name="audit-logs"),

    path(
        "password-reset/",
        views.PasswordResetRequestView.as_view(),
        name="password-reset",
    ),
    path(
        "password-reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),

    # Add this
    path(
        "password-change/",
        views.PasswordChangeView.as_view(),
        name="password-change",
    ),

    path("delete/", views.DeleteAccountView.as_view(), name="delete-account"),

    # MFA / TOTP (SFR-02b)
    path("mfa/status/", views.MFAStatusView.as_view(), name="mfa-status"),
    path("mfa/enrol/", views.MFAEnrolView.as_view(), name="mfa-enrol"),
    path("mfa/enrol/confirm/", views.MFAEnrolConfirmView.as_view(), name="mfa-enrol-confirm"),
    path("mfa/unenrol/", views.MFAUnenrolView.as_view(), name="mfa-unenrol"),
    path("mfa/verify-login/", views.MFALoginVerifyView.as_view(), name="mfa-verify-login"),
    path("staff/invite/", views.StaffInviteView.as_view(), name="staff-invite"),
    path("staff/accept-invite/", views.AcceptInviteView.as_view(), name="accept-invite"),
    path("admin/audit-log/", views.AdminAuditLogView.as_view(), name="admin-audit-log"),
    path("admin/users/", views.AdminUserListView.as_view(), name="admin-user-list"),
    path(
        "admin/users/<uuid:user_id>/",
        views.AdminUserDetailView.as_view(),
        name="admin-user-detail",
    ),
    path(
        "admin/users/<uuid:user_id>/terminate-sessions/",
        views.AdminTerminateSessionsView.as_view(),
        name="admin-terminate-sessions",
    ),
    path(
        "admin/users/<uuid:user_id>/demote/",
        views.AdminDemoteStaffView.as_view(),
        name="admin-demote-staff",
    ),
    path(
        "admin/users/<uuid:user_id>/promote/",
        views.AdminPromoteUserView.as_view(),
        name="admin-promote-user",
    ),
]
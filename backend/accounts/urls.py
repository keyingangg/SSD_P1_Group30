"""URL patterns for the accounts app."""
from django.urls import path

from . import views

urlpatterns = [
    path("csrf/", views.CSRFView.as_view(), name="csrf"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("verify-email/", views.VerifyEmailView.as_view(), name="verify-email"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("profile/", views.UserProfileView.as_view(), name="profile"),

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
    path("staff/invite/", views.StaffInviteView.as_view(), name="staff-invite"),
    path("staff/accept-invite/", views.AcceptInviteView.as_view(), name="accept-invite"),
    path("admin/users/", views.AdminUserListView.as_view(), name="admin-user-list"),
    path(
        "admin/users/<uuid:user_id>/",
        views.AdminUserDetailView.as_view(),
        name="admin-user-detail",
    ),
]
"""Custom middleware for SecureBid."""

import logging

from django.http import Http404

logger = logging.getLogger("securebid")


class SecurityHeadersMiddleware:
    """Attach hardening security headers to every response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # TODO: add CSP, Referrer-Policy, Permissions-Policy, X-Content-Type-
        # Options, and related security headers.
        return response


class RBACMiddleware:
    """Enforce admin-only access for admin pages and marked views."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, "user", None)
        path = request.path_info

        if path.startswith("/admin/"):
            if not user or not user.is_authenticated or not getattr(user, "is_staff", False):
                logger.warning(
                    "Blocked non-admin admin path request path=%s ip=%s agent=%s",
                    path,
                    request.META.get("REMOTE_ADDR"),
                    request.META.get("HTTP_USER_AGENT", ""),
                )
                raise Http404("Not found.")

        view_class = getattr(view_func, "view_class", None)
        if view_class and getattr(view_class, "staff_only", False):
            if not user or not user.is_authenticated or not getattr(user, "is_staff", False):
                logger.warning(
                    "Blocked non-admin API view request view=%s path=%s ip=%s agent=%s",
                    view_class.__name__,
                    path,
                    request.META.get("REMOTE_ADDR", ""),
                    request.META.get("HTTP_USER_AGENT", ""),
                )
                raise Http404("Not found.")

        return None

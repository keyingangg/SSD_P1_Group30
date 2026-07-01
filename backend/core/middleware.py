"""Custom middleware for SecureBid."""

import logging

from django.http import Http404
from django.utils.deprecation import MiddlewareMixin

from .audit import log_action

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


class RBACMiddleware(MiddlewareMixin):
    """Enforce admin-only access for admin pages and marked views.

    This middleware also emits audit log entries for denied access and for
    reads of audit-related endpoints (access to audit data must itself be
    auditable).
    """

    def process_request(self, request):
        # Log reads of audit-related endpoints (access itself must be auditable)
        path = request.path_info or ""
        if "audit" in path.lower() and request.method == "GET":
            try:
                log_action(
                    user=getattr(request, "user", None),
                    action="AUDIT_LOG_READ",
                    resource_type="audit_logs",
                    ip_address=request.META.get("REMOTE_ADDR"),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    request_method=request.method,
                    endpoint_path=path,
                    metadata={"note": "audit read attempted"},
                )
            except Exception:
                # Do not allow audit logging failures to block requests.
                pass

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, "user", None)
        path = request.path_info or ""

        if path.startswith("/admin/"):
            if not user or not user.is_authenticated or not getattr(user, "is_staff", False):
                logger.warning(
                    "Blocked non-admin admin path request path=%s ip=%s agent=%s",
                    path,
                    request.META.get("REMOTE_ADDR"),
                    request.META.get("HTTP_USER_AGENT", ""),
                )
                try:
                    log_action(
                        user=getattr(request, "user", None),
                        action="AUTHZ_DENIED",
                        resource_type="admin",
                        ip_address=request.META.get("REMOTE_ADDR"),
                        user_agent=request.META.get("HTTP_USER_AGENT", ""),
                        request_method=request.method,
                        endpoint_path=path,
                        metadata={"reason": "not_staff_or_not_authenticated"},
                    )
                except Exception:
                    pass
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
                try:
                    log_action(
                        user=getattr(request, "user", None),
                        action="AUTHZ_DENIED",
                        resource_type="api",
                        resource_id=None,
                        ip_address=request.META.get("REMOTE_ADDR"),
                        user_agent=request.META.get("HTTP_USER_AGENT", ""),
                        request_method=request.method,
                        endpoint_path=path,
                        metadata={"view": view_class.__name__},
                    )
                except Exception:
                    pass
                raise Http404("Not found.")

        return None

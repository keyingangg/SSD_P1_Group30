"""Custom middleware for SecureBid."""


class SecurityHeadersMiddleware:
    """Attach hardening security headers to every response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # TODO: add CSP, Referrer-Policy, Permissions-Policy, X-Content-Type-
        # Options, and related security headers.
        return response

"""Security response headers: Content-Security-Policy and no-store for signed-in users."""

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.cache import add_never_cache_headers

CSP_HEADER = "Content-Security-Policy"

# One strict policy for every page, the Django admin included (TASK-016): the templates
# and the Django 5.2 admin have no inline scripts, inline styles, inline event handlers,
# external URLs or data: URIs.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
    "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        # Django's technical error pages (DEBUG only) use inline styles and scripts.
        if settings.DEBUG and response.status_code >= 400:
            return response
        if CSP_HEADER not in response:
            response[CSP_HEADER] = CONTENT_SECURITY_POLICY
        return response


class PrivateCacheMiddleware:
    """Pages of a signed-in user must not stay in the browser cache after logout."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        # Without a session cookie the user is anonymous; do not touch the session then.
        if settings.SESSION_COOKIE_NAME not in request.COOKIES:
            return response
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            add_never_cache_headers(response)
        return response

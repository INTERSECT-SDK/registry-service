"""CSRF modules, this is only need if we choose to use cookies for session management."""

from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError

from ..core.environment import settings
from ..utils.htmx import do_universal_redirect
from ..utils.urls import url_abspath_for


def csrf_protect_exception_handler(request: Request, _: CsrfProtectError) -> Response:
    # First, try to use the user's Referer header to reload the page they were already on
    # DOES NOT WORK if Referrer-Policy does not send the full query string, this can be disabled by users' browsers or if referrer-policy is "no-referrer"
    # WARNING - this will always redirect to the website ROOT if referrer-policy is "strict-origin", this is also not easy to catch like the no-referrer check is
    referrer = request.headers['Referer']
    if referrer:
        return do_universal_redirect(request, request.headers['Referer'])

    # as a fallback log the user out and clear all CSRF and session tokens
    # this will only be reached from a POST method, and we will always redirect to a POST, therefore use 307
    # FIXME - this is currently causing issues with HTMX Keycloak
    return RedirectResponse(url_abspath_for(request, 'logout_request'), status_code=307)


@CsrfProtect.load_config
def get_csrf_config() -> tuple[tuple[str, str | bool], ...]:
    # if modifying return tuples, check the values of the "LoadConfig" dataclass: https://github.com/aekasitt/fastapi-csrf-protect/blob/master/src/fastapi_csrf_protect/load_config.py
    return (
        ('cookie_key', 'csrf-token'),
        ('cookie_samesite', 'strict'),
        ('secret_key', settings.SECRET_NAME),
        ('token_location', 'body'),  # only using CSRF for HTML forms
        ('token_key', 'csrf-token'),
        ('httponly', True),
        ('secure', True),
    )

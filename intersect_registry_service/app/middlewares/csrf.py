"""CSRF modules, this is only need if we choose to use cookies for session management."""

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError

from ..core.environment import settings
from ..utils.urls import url_abspath_for


def csrf_protect_exception_handler(request: Request, _: CsrfProtectError) -> RedirectResponse:
    # log the user out and clear all CSRF and session tokens
    # TODO potentially just reload the page?
    return RedirectResponse(url_abspath_for(request, 'logout_request'), status_code=303)


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

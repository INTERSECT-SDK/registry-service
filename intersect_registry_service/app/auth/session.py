from datetime import timedelta

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi_login import LoginManager

from ..core.environment import settings

LOGIN_URL = '/login'


class IntersectNotAuthenticatedError(Exception):
    """Exception the login manager throws if it can't authenticate the user."""


def handle_unauthenticated(request: Request, exc: Exception) -> RedirectResponse:  # noqa: ARG001
    """If the manager can't authenticate the user, redirect them to the login page."""
    return RedirectResponse(request.url_for('login_page'), status_code=303)


session_manager = LoginManager(
    settings.SECRET_NAME,
    LOGIN_URL,
    algorithm='HS256',  # default, can potentially use 'RS256'
    use_cookie=True,
    use_header=False,
    not_authenticated_exception=IntersectNotAuthenticatedError,
    default_expiry=timedelta(minutes=15),  # this is the default and seems like a good value
)
"""This login manager currently uses session cookies, but can potentially use JWT.

The current idea is to only use it as the authentication manager for UI endpoints, and use API keys for automated endpoints.
"""

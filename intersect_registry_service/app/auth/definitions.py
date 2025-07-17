from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from fastapi import Request
from fastapi.responses import RedirectResponse

USER = tuple[str, str]
"""
The defined typing is the return value of what the SessionManager looks up.

For now it's just a simple username/password tuple, may want to change this later (especially once we start defining roles).
"""


SESSION_COOKIE_NAME = 'session'

LOGIN_URL = '/login'


class IntersectNotAuthenticatedError(Exception):
    """Exception the session manager throws if it can't authenticate the user."""


def handle_unauthenticated(request: Request, exc: Exception) -> RedirectResponse:  # noqa: ARG001
    """If the session manager can't authenticate the user, redirect them to the login page."""
    return RedirectResponse(request.url_for('login_page'), status_code=303)


class SessionManager(Protocol):
    """
    Common authentication interface we use across the application
    """

    @property
    def cookie_name(self) -> str: ...

    def user_loader(self, *args: Any, **kwargs: Any) -> Callable | Callable[..., Awaitable]:  # type: ignore  # noqa: PGH003
        """
        Internal config only, loads the function for getting user credentials from the username.
        """

    async def optional(self, request: Request, *args: Any, **kwargs: Any) -> USER | None:
        """
        Allow for an endpoint to be accessed if unauthenticated, but handle user differently based on authentication status

        (if you handle all users in the same way, don't bother calling the session manager)
        """

    async def __call__(self, request: Request, *args: Any, **kwds: Any) -> USER:
        """
        If called directly, this implies that the endpoint may only be accessed if authenticated.
        """

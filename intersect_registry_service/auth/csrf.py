"""CSRF modules, this is only need if we choose to use cookies for session management."""

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError

from ..core.environment import settings


def csrf_protect_exception_handler(_: Request, exc: CsrfProtectError) -> JSONResponse:  # noqa: ARG001
    # NOTE - this probably shouldn't be seen by a normal user, so this may not necessarily be the best way to handle it
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.message})


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

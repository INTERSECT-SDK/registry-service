import logging

from fastapi import HTTPException, Request
from fastapi.responses import PlainTextResponse

_log = logging.getLogger('')


async def catch_exceptions_middleware(request: Request, exc: Exception) -> PlainTextResponse:
    """Makes sure that exceptions are logged and that we return a nondescript error to users if we didn't catch the exception."""
    if isinstance(exc, HTTPException):
        # we already caught this exception, it's most likely a 400-level error
        # log it for the sake of checking for malicious input and continue on
        _log.warning(
            'Invalid client request raised exception %s, full request info: %s', exc, request
        )
        raise exc

    # otherwise, we didn't already handle the exception, so it's our fault
    _log.exception(exc)
    return PlainTextResponse('Internal server error', status_code=500)

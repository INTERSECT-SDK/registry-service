import hashlib
import inspect
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any

from anyio.to_thread import run_sync
from fastapi import Request

from ...core.environment import settings
from ...core.log_config import logger
from ..definitions import SESSION_COOKIE_NAME, USER, IntersectNotAuthenticatedError, SessionManager

LOGIN_URL = '/login'


class CookieSessionManager:
    def __init__(self, cookie_name: str) -> None:
        self._user_callback: partial | None = None
        self.cookie_name = cookie_name

    async def __call__(
        self,
        request: Request,
    ) -> USER:
        if request.session:
            fingerprint_cookie = request.cookies.get(settings.SESSION_FINGERPRINT_COOKIE, None)
            token = request.session.get('user', None)
            fingerprint_hash = request.session.get('fingerprint_hash', None)
            if fingerprint_cookie and fingerprint_hash:
                sha_hash = hashlib.sha256()
                sha_hash.update(fingerprint_cookie.encode('utf-8'))
                digest = sha_hash.hexdigest()
                if digest != fingerprint_hash:
                    err_msg = 'Fingerprint is invalid.'
                    raise IntersectNotAuthenticatedError(err_msg)
            else:
                # We might want to display these authentication errors to the user if they can do something about them
                err_msg = 'Fingerprint is invalid.'
                raise IntersectNotAuthenticatedError(err_msg)
            return await self.get_user(token)
        err_msg = 'Invalid Login.'
        raise IntersectNotAuthenticatedError(err_msg)

    async def optional(
        self,
        request: Request,
    ) -> USER | None:
        """
        Acts as a dependency which catches all errors and returns `None` instead
        """
        try:
            user = await self.__call__(
                request,
            )
        except Exception as e:  # noqa: BLE001
            if not isinstance(e, IntersectNotAuthenticatedError):
                logger.error(e)
            return None
        else:
            return user

    async def get_user(self, identifier: Any) -> USER:
        if self._user_callback is None:
            msg = 'Missing user_loader callback.'
            raise IntersectNotAuthenticatedError(msg)

        if inspect.iscoroutinefunction(self._user_callback):
            user = await self._user_callback(identifier)
        else:
            user = await run_sync(self._user_callback, identifier)

        return user

    def user_loader(self, *args: Any, **kwargs: Any) -> Callable | Callable[..., Awaitable]:
        def decorator(callback: Callable | Callable[..., Awaitable]) -> Any:
            self._user_callback = partial(callback, *args, **kwargs)
            return callback

        return decorator


session_manager: SessionManager = CookieSessionManager(cookie_name=SESSION_COOKIE_NAME)
"""This login manager currently uses session cookies, but can potentially use JWT.

The current idea is to only use it as the authentication manager for UI endpoints, and use API keys for automated endpoints.
"""

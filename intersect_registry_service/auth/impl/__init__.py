from collections.abc import Callable

from ...core.environment import settings
from ..user import USER

get_user: Callable[[str], USER | None] = None  # type: ignore[assignment]
"""
This function should return any credentials necessary.

For the rudimentary approach, it's returning the username and the password, though we probably don't want the password.
"""

if settings.AUTH_IMPLEMENTATION == 'keycloak':
    raise NotImplementedError
else:
    from .rudimentary import get_user_impl

    get_user = get_user_impl

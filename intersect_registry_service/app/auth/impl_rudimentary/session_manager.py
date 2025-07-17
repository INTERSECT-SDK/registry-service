from datetime import timedelta

from fastapi_login import LoginManager

from ...core.environment import settings
from ..definitions import (
    LOGIN_URL,
    SESSION_COOKIE_NAME,
    IntersectNotAuthenticatedError,
    SessionManager,
)

session_manager: SessionManager = LoginManager(
    settings.SECRET_NAME,
    LOGIN_URL,
    algorithm='HS256',  # default, can potentially use 'RS256'
    use_cookie=True,
    cookie_name=SESSION_COOKIE_NAME,
    use_header=False,
    not_authenticated_exception=IntersectNotAuthenticatedError,
    default_expiry=timedelta(minutes=15),  # this is the default and seems like a good value
)

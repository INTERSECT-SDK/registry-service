import jwt
from jwt import PyJWKClient

from ...core.environment import settings
from ...core.log_config import logger
from ..definitions import USER, IntersectNotAuthenticatedError

_jwks_client = PyJWKClient(settings.keycloak_jwks_url)
"""
This object handles caching, so it needs to be a global singleton

See: https://blog.ploetzli.ch/2024/pyjwt-django-resource-server-sane/
"""


def get_user(user_token: str) -> None | USER:
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(user_token).key
        user = jwt.decode(
            user_token,
            signing_key,
            algorithms=['RS256'],
            verify=True,
            options={'verify_signature': True, 'verify_aud': False},
        )
        username = user.get('preferred_username', None)
        if not username:
            # all tokens should at least have email if email scope is requested
            username = username['email']
        return username, user_token  # noqa: TRY300
    except Exception as e:
        logger.error('%s', e)
        raise IntersectNotAuthenticatedError from e
    return None

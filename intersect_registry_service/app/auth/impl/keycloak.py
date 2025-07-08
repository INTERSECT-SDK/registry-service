import jwt
from jwt import PyJWKClient

from intersect_registry_service.app.auth.session import IntersectNotAuthenticatedError

from ...core.environment import settings
from ...core.log_config import logger
from ..user import USER


def get_user_impl(token: str) -> None | USER:
    try:
        verify = False
        signing_key = ''
        algorithms = []
        if settings.SESSION_VERIFY_ID:
            jwks_client = PyJWKClient(settings.JWKS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            verify = True
            algorithms = ['RS256']
        user = jwt.decode(
            token,
            signing_key,
            algorithms=algorithms,
            verify=verify,
            options={'verify_signature': verify},
        )
        username = user.get('preferred_username', None)
        if not username:
            # all tokens should at least have email if email scope is requested
            username = username['email']
        return username, token  # noqa: TRY300
    except Exception as e:
        logger.error(e)
        raise IntersectNotAuthenticatedError from e
    return None

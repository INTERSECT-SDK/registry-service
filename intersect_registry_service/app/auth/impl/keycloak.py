import jwt
from jwt import PyJWKClient

from ...core.environment import settings
from ...core.log_config import logger
from ..user import USER


def get_user_impl(token: str) -> None | USER:
    try:
        jwks_client = PyJWKClient(settings.JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        user = jwt.decode(token, signing_key, algorithms=['RS256'], verify=True)
        username = user.get('preferred_username', None)
        if not username:
            # all tokens should at least have email if email scope is requested
            username = username['email']
        return username, token  # noqa: TRY300
    except Exception as e:  # noqa: BLE001
        logger.error(e)
    return None

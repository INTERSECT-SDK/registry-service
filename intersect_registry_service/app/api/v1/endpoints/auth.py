import hashlib
import random
import string

import jwt
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from starlette.config import Config
from starlette.requests import Request

from ....auth.session import session_manager
from ....core.environment import settings

router = APIRouter()

config = Config(environ={})
oauth_session = OAuth(config)
oauth_session.register(
    'keycloak',
    authorize_url=settings.AUTHORIZE_URL,
    access_token_url=settings.TOKEN_URL,
    scope=settings.SCOPE,
    client_id=settings.CLIENT_ID,
    client_secret=settings.CLIENT_SECRET,
    jwks_uri=settings.JWKS_URL,
)


@router.get('/auth/callback')
async def auth_handler(request: Request) -> RedirectResponse:
    token = await oauth_session.keycloak.authorize_access_token(request)
    id_token = token['id_token']
    request.session['user'] = id_token
    response = RedirectResponse(request.url_for('microservice_user_page'), status_code=303)

    fingerprint = ''.join(
        random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(32)
    )

    # Create SHA-256 hash of fingerprint
    sha_hash = hashlib.sha256()
    sha_hash.update(fingerprint.encode('utf-8'))
    digest = sha_hash.hexdigest()
    request.session['fingerprint_hash'] = digest
    encoded_session = jwt.encode(
        payload=request.session, key=settings.SESSION_SECRET, algorithm='HS256'
    )
    response.set_cookie(
        key=session_manager.cookie_name,
        value=encoded_session,
        secure=True,
        httponly=True,
        samesite='lax',
        max_age=settings.SESSION_MAX_AGE,
    )
    # Set fingerprint cookie
    response.set_cookie(
        key=settings.SESSION_FINGERPRINT_COOKIE,
        value=fingerprint,
        secure=True,
        httponly=True,
        samesite='lax',
        max_age=settings.SESSION_MAX_AGE,
    )
    return response


@router.get('/auth/login')
async def login_link(request: Request) -> RedirectResponse:
    return await oauth_session.keycloak.authorize_redirect(request, settings.REDIRECT_URL)

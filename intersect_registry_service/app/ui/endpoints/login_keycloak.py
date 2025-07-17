import hashlib
import random
import string
import urllib.parse
from typing import Annotated

import jwt
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from starlette.config import Config
from starlette.requests import Request

from ...auth import session_manager
from ...auth.definitions import LOGIN_URL, USER
from ...core.environment import settings
from ...utils.html_security_headers import get_html_security_headers, get_nonce
from ..templating import TEMPLATES

router = APIRouter()

config = Config(environ={})
oauth_session = OAuth(config)
oauth_session.register(
    'keycloak',
    authorize_url=settings.keycloak_authorize_url,
    access_token_url=settings.keycloak_token_url,
    scope=settings.SCOPE,
    client_id=settings.CLIENT_ID,
    client_secret=settings.CLIENT_SECRET,
    jwks_uri=settings.keycloak_jwks_url,
)


@router.get(f'{LOGIN_URL}/callback')
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


@router.get(f'{LOGIN_URL}/redirect')
async def login_redirect(request: Request) -> RedirectResponse:
    return await oauth_session.keycloak.authorize_redirect(request, settings.login_redirect_url)


@router.get(LOGIN_URL)
async def login_page(
    request: Request, user: Annotated[USER, Depends(session_manager.optional)]
) -> RedirectResponse:
    if user is not None:
        return RedirectResponse(request.url_for('microservice_user_page'))
    # return await oauth_session.keycloak.authorize_redirect(request, settings.login_redirect_url)

    nonce = get_nonce()
    headers = get_html_security_headers(nonce)
    return TEMPLATES.TemplateResponse(
        request=request,
        name='keycloak-login-page.jinja',
        context={
            'nonce': nonce,
        },
        headers=headers,
    )


@router.post('/logout', response_class=RedirectResponse, dependencies=[Depends(session_manager)])
async def logout_callback(request: Request) -> RedirectResponse:
    user = request.session.get('user')
    if user:
        request.session.pop('user')
        app_redirect_uri = urllib.parse.quote_plus(str(request.url_for('login_page')))
        keycloak_url = f'{settings.keycloak_logout_url}?post_logout_redirect_uri={app_redirect_uri}&id_token_hint={urllib.parse.quote_plus(user)}'
        response = RedirectResponse(keycloak_url, status_code=303)
    else:
        response = RedirectResponse(request.url_for('login_page'), status_code=303)

    response.delete_cookie(
        session_manager.cookie_name,
        secure=True,
        httponly=True,
        samesite='strict',
    )
    response.delete_cookie(
        'csrf-token',
        secure=True,
        httponly=True,
        samesite='strict',
    )
    response.delete_cookie(
        settings.SESSION_FINGERPRINT_COOKIE,
        secure=True,
        httponly=True,
        samesite='strict',
    )
    return response

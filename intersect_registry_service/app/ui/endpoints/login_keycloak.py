import hashlib
import random
import string
import urllib.parse
from typing import Annotated

import jwt
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, RedirectResponse
from starlette.config import Config
from starlette.requests import Request

from ...auth import session_manager
from ...auth.definitions import LOGIN_URL, USER
from ...core.environment import settings
from ...utils.html_security_headers import get_html_security_headers, get_nonce
from ...utils.urls import absolute_url_for, url_abspath_for
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
async def login_callback(request: Request) -> RedirectResponse:
    token = await oauth_session.keycloak.authorize_access_token(request)
    id_token = token['id_token']
    request.session['user'] = id_token
    response = RedirectResponse(url_abspath_for(request, 'microservice_user_page'), status_code=303)

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
    url_for = absolute_url_for(request, 'login_callback')
    if not url_for:
        return PlainTextResponse('Internal server error', status_code=500)  # type: ignore[return-value]
    return await oauth_session.keycloak.authorize_redirect(request, url_for)


@router.get(LOGIN_URL)
async def login_page(
    request: Request, user: Annotated[USER, Depends(session_manager.optional)]
) -> RedirectResponse:
    if user is not None:
        return RedirectResponse(url_abspath_for(request, 'microservice_user_page'))

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
async def logout_request(request: Request) -> RedirectResponse:
    user = request.session.get('user')
    if user:
        request.session.pop('user')
        url_for = absolute_url_for(request, 'login_page')
        if url_for:
            app_redirect_uri = urllib.parse.quote_plus(str(url_for))
            keycloak_url = f'{settings.keycloak_logout_url}?post_logout_redirect_uri={app_redirect_uri}&id_token_hint={urllib.parse.quote_plus(user)}'
        else:
            keycloak_url = (
                f'{settings.keycloak_logout_url}?id_token_hint={urllib.parse.quote_plus(user)}'
            )
        response = RedirectResponse(keycloak_url, status_code=303)
    else:
        response = RedirectResponse(url_abspath_for(request, 'login_page'), status_code=303)

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
        samesite='lax',
    )
    return response

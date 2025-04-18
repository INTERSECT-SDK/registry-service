from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_csrf_protect import CsrfProtect

from ...auth.impl import get_user
from ...auth.session import LOGIN_URL, session_manager
from ...auth.user import USER
from ...utils.html_security_headers import get_html_security_headers, get_nonce
from ..templating import TEMPLATES

router = APIRouter()


CTX_USERNAME = 'x-app-login-username'
CTX_INVALID = 'x-app-login-invalid'


@router.get(LOGIN_URL, response_class=HTMLResponse)
async def login_page(
    request: Request,
    user: Annotated[USER, Depends(session_manager.optional)],
    csrf_protect: Annotated[CsrfProtect, Depends()],
) -> HTMLResponse:
    if user is not None:
        return RedirectResponse('/')  # type: ignore[return-value]
    username = request.cookies.get(CTX_USERNAME, '')
    user_error = bool(request.cookies.get(CTX_INVALID))

    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

    nonce = get_nonce()
    headers = get_html_security_headers(nonce)
    response = TEMPLATES.TemplateResponse(
        request=request,
        name='login-page.jinja',
        context={
            'nonce': nonce,
            'csrf_token': csrf_token,
            'username': username,
            'user_error': user_error,
        },
        headers=headers,
    )
    if username:
        response.delete_cookie(
            CTX_USERNAME,
            secure=True,
            httponly=True,
            samesite='strict',
        )
    if user_error:
        response.delete_cookie(
            CTX_INVALID,
            secure=True,
            httponly=True,
            samesite='strict',
        )
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@router.post(LOGIN_URL, response_class=RedirectResponse)
async def login_request(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    user: Annotated[USER, Depends(session_manager.optional)],
    csrf_protect: Annotated[CsrfProtect, Depends()],
) -> RedirectResponse:
    await csrf_protect.validate_csrf(request)
    if user is not None:
        response = RedirectResponse('/', status_code=302)
        csrf_protect.unset_csrf_cookie(response)
        return response
    auth_user = get_user(username)
    if not auth_user or password != auth_user[1]:
        response = RedirectResponse('/', status_code=302)
        response.set_cookie(
            CTX_USERNAME,
            username,
            secure=True,
            httponly=True,
            samesite='strict',
        )
        response.set_cookie(
            CTX_INVALID,
            'true',
            secure=True,
            httponly=True,
            samesite='strict',
        )
        csrf_protect.unset_csrf_cookie(response)
        return response

    access_token = session_manager.create_access_token(data={'sub': auth_user[0]})
    response = RedirectResponse('/', status_code=302)
    response.set_cookie(
        session_manager.cookie_name,
        access_token,
        secure=True,
        httponly=True,
        samesite='strict',
    )
    csrf_protect.unset_csrf_cookie(response)
    return response


@router.post('/logout', response_class=RedirectResponse, dependencies=[Depends(session_manager)])
async def logout_request() -> RedirectResponse:
    response = RedirectResponse(LOGIN_URL, status_code=302)
    response.delete_cookie(
        session_manager.cookie_name,
        secure=True,
        httponly=True,
        samesite='strict',
    )
    return response

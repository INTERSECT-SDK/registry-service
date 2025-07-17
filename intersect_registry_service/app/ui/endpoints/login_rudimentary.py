from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_csrf_protect import CsrfProtect

from ...auth import get_user, session_manager
from ...auth.definitions import LOGIN_URL, USER
from ...utils.html_security_headers import get_html_security_headers, get_nonce
from ...utils.htmx import is_htmx_request
from ..templating import TEMPLATES

router = APIRouter()


@router.get(LOGIN_URL, response_class=HTMLResponse)
async def login_page(
    request: Request,
    user: Annotated[USER, Depends(session_manager.optional)],
    csrf_protect: Annotated[CsrfProtect, Depends()],
    username: Annotated[str, Query()] = '',
    err: Annotated[str, Query()] = '',
) -> HTMLResponse:
    if user is not None:
        return RedirectResponse(request.url_for('microservice_user_page'))  # type: ignore[return-value]

    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

    nonce = get_nonce()
    headers = get_html_security_headers(nonce)
    response = TEMPLATES.TemplateResponse(
        request=request,
        name='non-keycloak-login-page.jinja',
        context={
            'nonce': nonce,
            'csrf_token': csrf_token,
            'username': username,
            'err': err,
        },
        headers=headers,
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
        response = RedirectResponse(request.url_for('microservice_user_page'), status_code=303)
        csrf_protect.unset_csrf_cookie(response)
        return response
    auth_user = get_user(username)
    if not auth_user or password != auth_user[1]:
        err_ctx = {'username': username, 'err': '1'}
        if is_htmx_request(request):
            return TEMPLATES.TemplateResponse(
                request=request,
                name='login-page-error-partial.jinja',
                context=err_ctx,
                headers={
                    'HX-Retarget': '#login-form-errors',
                },
            )
        response = RedirectResponse(
            request.url_for('login_page').include_query_params(**err_ctx), status_code=303
        )
        csrf_protect.unset_csrf_cookie(response)
        return response

    access_token = session_manager.create_access_token(data={'sub': auth_user[0]})
    response = RedirectResponse(request.url_for('microservice_user_page'), status_code=303)
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
async def logout_request(request: Request) -> RedirectResponse:
    response = RedirectResponse(request.url_for('login_page'), status_code=303)
    response.delete_cookie(
        session_manager.cookie_name,
        secure=True,
        httponly=True,
        samesite='strict',
    )
    if request.session:
        request.session.pop('user', None)
    return response

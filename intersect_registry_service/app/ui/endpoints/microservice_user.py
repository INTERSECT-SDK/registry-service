from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from ...auth.session import session_manager
from ...auth.user import USER
from ...core.definitions import HIERARCHY_REGEX
from ...core.environment import settings
from ...core.log_config import logger
from ...models.broker import Broker
from ...models.service import Service
from ...utils.api_keys import make_api_key
from ...utils.html_security_headers import get_html_security_headers, get_nonce
from ...utils.htmx import is_htmx_request
from ..templating import TEMPLATES

router = APIRouter()


CTX_INVALID_SERVICE = 'x-app-microservice-invalid'
CTX_SERVER_ERROR_SERVICE = 'x-app-microservice-misc'


@router.get('/', response_class=HTMLResponse)
async def microservice_user_page(
    request: Request,
    user: Annotated[USER, Depends(session_manager)],
    csrf_protect: Annotated[CsrfProtect, Depends()],
    invalid_service: str | None = Query('', alias='svc'),
    server_fault: str | None = Query('', alias='err'),
) -> HTMLResponse:
    logger.info('test')
    username = user[0]
    with Session(request.app.state.db) as session:
        statement = (
            select(Service)
            .where(Service.username == username)
            .order_by(col(Service.last_modified).desc())
        )
        results = session.exec(statement).fetchall()

    nonce = get_nonce()
    headers = get_html_security_headers(nonce)
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = TEMPLATES.TemplateResponse(
        request=request,
        name='microservice-user-page.jinja',
        context={
            'nonce': nonce,
            'csrf_token': csrf_token,
            'system_name': settings.SYSTEM_NAME,
            'client_api_key': settings.BROKER_CLIENT_API_KEY,
            'services': results,
            'svc': invalid_service,
            'err': server_fault,
            'username': username,
        },
        headers=headers,
    )
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@router.post('/')
async def add_new_service(
    request: Request,
    service_name: Annotated[str, Form(pattern=HIERARCHY_REGEX)],
    user: Annotated[USER, Depends(session_manager)],
    csrf_protect: Annotated[CsrfProtect, Depends()],
) -> Response:
    await csrf_protect.validate_csrf(request)

    username = user[0]
    api_key = make_api_key()

    new_service = None
    with Session(request.app.state.db) as session:
        try:
            new_service = Service(service_name=service_name, username=username, api_key=api_key)
            session.add(new_service)
            session.commit()
            session.refresh(new_service)
        except IntegrityError:
            # user attempted to violate service_name unique constraint
            return _add_new_service_error(request, csrf_protect, service_name, server_fault=False)
        except Exception:  # noqa: BLE001
            return _add_new_service_error(request, csrf_protect, service_name, server_fault=True)

    try:
        broker_user, broker_password = request.app.state.config_manager.add_service(service_name)
        with Session(request.app.state.db) as session:
            new_broker = Broker(broker_password=broker_password, service=new_service)
            session.add(new_broker)
            session.commit()
            session.refresh(new_broker)
            session.refresh(new_service)
    except Exception:  # noqa: BLE001
        logger.exception('Could not setup brokers for service: %s', new_service.service_name)
        try:
            with Session(request.app.state.db) as session:
                session.delete(new_service)
                session.commit()
        except Exception:  # noqa: BLE001
            logger.exception(
                'Could not implement failsafe rollback for service %s, will need to manually remove it',
                new_service.service_name,
            )
        return _add_new_service_error(request, csrf_protect, service_name, server_fault=True)

    if is_htmx_request(request):
        # Javascript is enabled, so we can return an HTML partial
        return TEMPLATES.TemplateResponse(
            request=request, name='service-list-partial.jinja', context={'services': [new_service]}
        )

    # no Javascript detected, use the Post-Redirect-Get fallback
    response = RedirectResponse(request.url_for('microservice_user_page'), status_code=303)
    csrf_protect.unset_csrf_cookie(response)
    return response


def _add_new_service_error(
    request: Request, csrf_protect: CsrfProtect, service_name: str, server_fault: bool
) -> Response:
    err_ctx = {'svc': service_name}
    if server_fault:
        err_ctx.update({'err': '1'})
    if is_htmx_request(request):
        # Javascript is enabled, so we can return an HTML partial
        # we are now REPLACING the error LAST CHILD of the FORM, instead of APPENDING as the FIRST CHILD of the TABLE BODY
        return TEMPLATES.TemplateResponse(
            request=request,
            name='service-submit-error-partial.jinja',
            context=err_ctx,
            headers={
                'HX-Reswap': 'innerHTML',
                'HX-Retarget': '#service-submit-form-errors',
            },
        )

    # No Javascript detected, use the Post-Redirect-Get fallback
    response = RedirectResponse(
        request.url_for('microservice_user_page').include_query_params(**err_ctx), status_code=303
    )
    csrf_protect.unset_csrf_cookie(response)
    return response

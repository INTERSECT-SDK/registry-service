"""These are the 'real' endpoints called by the SDK in a production environment."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Security
from sqlalchemy.exc import NoResultFound
from sqlmodel import Session, select

from .....core.environment import settings
from .....models.service import Service
from .....utils.client_name_generator import generate_client_name
from ...api_key import api_key_header
from .definitions import ControlPlaneConfig, IntersectClientConfig, IntersectConfig

router = APIRouter()


@router.get(
    '/service_config',
    description='Get dynamic INTERSECT config from your Service name and its API key. Requires pre-registration.',
    response_description=(
        'The response type used by INTERSECT-SDK clients to understand how to connect to the INTERSECT ecosystem.'
    ),
)
async def service_config(
    req: Request,
    service_name: Annotated[str, Query(min_length=3, max_length=63)],
    api_key: Annotated[str, Security(api_key_header)],
) -> IntersectConfig:
    with Session(req.app.state.db) as session:
        statement = (
            select(Service)
            .where(Service.service_name == service_name, Service.api_key == api_key)
            .limit(1)
        )
        try:
            session.exec(statement).one()
        except NoResultFound:  # don't need to check for multiple because of DB constraints
            raise HTTPException(  # noqa: B904
                status_code=403,
                detail=f"Service namespace '{service_name}' either has not been registered yet or you have sent an invalid API key. You will need to manually register the key in the UI if it has not been registered yet.",
            )

    return IntersectConfig(
        system_name=settings.SYSTEM_NAME,
        brokers=[
            ControlPlaneConfig(
                protocol=settings.BROKER_PROTOCOL,
                uri='iwillconstructthislater',
                tls=settings.BROKER_TLS_CERT,
            ),
        ],
    )


@router.get(
    '/client_config',
    description='Get dynamic INTERSECT config for a Client. Requires knowledge of the Client API key.',
    response_description='The response type used by INTERSECT-SDK Clients to understand how to connect to the INTERSECT ecosystem.',
)
async def client_config(
    api_key: Annotated[str, Security(api_key_header)],
) -> IntersectClientConfig:
    if api_key != settings.BROKER_CLIENT_API_KEY:
        raise HTTPException(status_code=403, detail='Invalid API key in Authorization header')

    client_name = generate_client_name()
    return IntersectClientConfig(
        system_name=settings.SYSTEM_NAME,
        brokers=[
            ControlPlaneConfig(
                protocol=settings.BROKER_PROTOCOL,
                uri=settings.broker_client_uri,
                tls=settings.BROKER_TLS_CERT,
            ),
        ],
        client_name=client_name,
    )

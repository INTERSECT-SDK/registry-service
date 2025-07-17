"""Quick access endpoints, mostly for SDK developers E2E testing their setup. Do NOT use if you don't control the broker."""

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from .....core.definitions import get_raw_protocol, get_uri_path
from .....core.environment import settings
from .....utils.client_name_generator import generate_client_name
from .definitions import ControlPlaneConfig, IntersectClientConfig, IntersectConfig

router = APIRouter()


@router.get(
    '/service_config',
    description='DEVELOPMENT USAGE ONLY: Get broker config for your local INTERSECT-SDK Service.',
    response_description=(
        'The response type used by INTERSECT-SDK clients to understand how to connect to the INTERSECT ecosystem.'
    ),
)
async def debug_service_config(
    api_key: Annotated[str, Header(alias='Authorization')],
) -> IntersectConfig:
    if api_key != settings.DEVELOPMENT_API_KEY:
        raise HTTPException(status_code=403, detail='Invalid API key in Authorization header')

    # in Debug mode, we will just use the root broker credentials, and not worry about using a different user
    root_broker_uri = f'{get_raw_protocol(settings.BROKER_PROTOCOL, bool(settings.BROKER_TLS_CERT))}://{settings.BROKER_ROOT_USERNAME}:{settings.BROKER_ROOT_PASSWORD}@{settings.BROKER_HOST}:{settings.BROKER_PORT}{get_uri_path(settings.BROKER_PROTOCOL)}'

    return IntersectConfig(
        system_name=settings.SYSTEM_NAME,
        brokers=[
            ControlPlaneConfig(
                protocol=settings.BROKER_PROTOCOL,
                uri=root_broker_uri,
                tls=settings.BROKER_TLS_CERT,
            ),
        ],
    )


@router.get(
    '/client_config',
    description='DEVELOPMENT USAGE ONLY: Get broker config for your local INTERSECT-SDK Client.',
    response_description='The response type used by INTERSECT-SDK Clients to understand how to connect to the INTERSECT ecosystem.',
)
async def client_config_debug(
    api_key: Annotated[str, Header(alias='Authorization')],
) -> IntersectClientConfig:
    if api_key != settings.BROKER_CLIENT_API_KEY:
        raise HTTPException(status_code=403, detail='Invalid API key in Authorization header')

    # in Debug mode, we will just use the root broker credentials, and not worry about using a different user
    root_broker_uri = f'{get_raw_protocol(settings.BROKER_PROTOCOL, bool(settings.BROKER_TLS_CERT))}://{settings.BROKER_ROOT_USERNAME}:{settings.BROKER_ROOT_PASSWORD}@{settings.BROKER_HOST}:{settings.BROKER_PORT}{get_uri_path(settings.BROKER_PROTOCOL)}'
    client_name = generate_client_name()
    return IntersectClientConfig(
        system_name=settings.SYSTEM_NAME,
        brokers=[
            ControlPlaneConfig(
                protocol=settings.BROKER_PROTOCOL,
                uri=root_broker_uri,
                tls=settings.BROKER_TLS_CERT,
            ),
        ],
        client_name=client_name,
    )

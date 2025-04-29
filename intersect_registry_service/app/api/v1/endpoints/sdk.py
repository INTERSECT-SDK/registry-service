from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import NoResultFound
from sqlmodel import Session, select

from ....core.definitions import BrokerProtocol
from ....core.environment import settings
from ....models.service import Service
from ....utils.client_name_generator import generate_client_name

router = APIRouter()


class ControlPlaneConfig(BaseModel):
    """The configuration used by the INTERSECT-SDK control plane"""

    protocol: BrokerProtocol
    """Explicitly separating out the protocol allows us to do control flow parsing on the SDK"""
    uri: str
    """This is the fully qualified URI to connect to the broker. Will include the protocol, host, port, username, password, path, and any query parameters."""
    tls: str | None = None
    """The TLS certificate, which may or may not exist."""


class MinioConfig(BaseModel):
    """MINIO-specific config"""

    type: Literal['minio']
    """Basic discriminator type for control flow logic"""
    url: str
    """This is the fully qualified URL to connect to the MINIO instance. Will include the protocol, host, port, username, and password."""


DataPlaneConfig = Annotated[MinioConfig, Field(discriminator='type')]
"""The configuration used by the INTERSECT-SDK data plane"""


class IntersectConfig(BaseModel):
    """The response type used by INTERSECT-SDK Services and Clients to understand how to connect to the INTERSECT ecosystem.

    The values returned from this response can be potentially rotated, so you should NOT attempt to utilize the values cached on the microservice/client unless this server gives you the go-ahead.
    """

    system_name: str
    """The system namespacing of these credentials. Important for various interactions on both the control plane and the data plane."""
    brokers: Annotated[list[ControlPlaneConfig], Field(min_length=1)]
    """List of control plane configurations the SDK should use."""
    data_stores: list[DataPlaneConfig] = []
    """List of data plane configurations the SDK should use."""


class IntersectClientConfig(IntersectConfig):
    """Response type used by INTERSECT-SDK Clients to understand how to connect to the INTERSECT ecosystem"""

    client_name: str
    """A randomly-generated temporary name, unique to your Client."""


if settings.DEVELOPMENT_API_KEY:
    # setup endpoint for easy LOCAL testing - you should ONLY use this if your broker is also local
    from ....core.definitions import get_raw_protocol, get_uri_path

    @router.get(
        '/service_config',
        description='DEVELOPMENT USAGE ONLY: Get broker config for your local INTERSECT-SDK Service.',
        response_description=(
            'The response type used by INTERSECT-SDK clients to understand how to connect to the INTERSECT ecosystem.'
        ),
        response_model=IntersectConfig,
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
        response_model=IntersectClientConfig,
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
else:

    @router.get(
        '/service_config',
        description='Get dynamic INTERSECT config from your Service name and its API key. Requires pre-registration.',
        response_description=(
            'The response type used by INTERSECT-SDK clients to understand how to connect to the INTERSECT ecosystem.'
        ),
        response_model=IntersectConfig,
    )
    async def service_config(
        req: Request,
        service_name: Annotated[str, Query(min_length=3, max_length=63)],
        api_key: Annotated[str, Header(alias='Authorization')],
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
        response_model=IntersectClientConfig,
    )
    async def client_config(
        api_key: Annotated[str, Header(alias='Authorization')],
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

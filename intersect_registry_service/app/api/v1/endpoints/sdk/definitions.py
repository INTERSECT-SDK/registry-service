from typing import Annotated, Literal

from pydantic import BaseModel, Field

from .....core.definitions import BrokerProtocol


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

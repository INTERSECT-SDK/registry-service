from functools import cached_property
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, HttpUrl, PositiveInt
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

from .definitions import (
    HIERARCHY_REGEX,
    BrokerProtocol,
    get_raw_protocol,
    get_uri_path,
)

LogLevel = Literal['CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'WARN', 'INFO', 'DEBUG']


def strip_trailing_slash(value: str) -> str:
    value.rstrip('/')
    return value


StripTrailingSlash_str = Annotated[str, BeforeValidator(strip_trailing_slash)]


class Settings(BaseSettings):
    """variables which can be loaded as environment variables.

    For a valid local setup, see .env.example
    """

    ### GENERIC APP CONFIG ###

    LOG_LEVEL: LogLevel = Field(default='INFO')
    """Log level for the ENTIRE application"""
    PRODUCTION: bool = False
    """If True, this flag enables a few different settings:

    1) Binds to 0.0.0.0 instead of 127.0.0.1
    2) Format logs in JSON instead of the "pretty" format
    3) Turns off uvicorn reload
    """

    SERVER_PORT: PositiveInt = 8000
    """The port Uvicorn will try to run on"""
    SERVER_WORKERS: PositiveInt = 1
    """Number of workers for Uvicorn."""
    DOMAIN: HttpUrl = HttpUrl('http://localhost:8000')
    """
    This is the protocol + DNS name of the website, without the path. Used for some callback URLs.
    """
    BASE_URL: StripTrailingSlash_str = ''
    """Set this to '' if this is not behind a proxy, set this to your proxy's path if this is behind a proxy.

    Do not include the full URI, only include the path component.
    """
    ROOT_DIR: Path = Field(default=Path(__file__).parents[3].absolute())
    """The directory to where we execute the script from, mostly to point to shared files. This should ALWAYS be an absolute path.

    'Shared files' currently comprises just the migration scripts (always called 'migrations') and alembic.ini . For simplicity's sakes, the files are always assumed to have the same names from the root directory.

    This doesn't need to be changed while developing. It should be set for you automatically in Docker. If running this via an init system like systemd, you'll need to manually set up a directory.
    """

    @cached_property
    def login_redirect_url(self) -> str:
        """
        The OIDC provider will redirect to this path after authentication.
        """
        return f'{strip_trailing_slash(str(self.DOMAIN))}{self.BASE_URL}login/callback'

    @cached_property
    def logout_redirect_url(self) -> str:
        """
        The OIDC provider will redirect to this path after signing out.
        """
        return f'{strip_trailing_slash(str(self.DOMAIN))}{self.BASE_URL}logout/callback'

    ### AUTHENTICATION CONFIGS (allows for enabling/disabling certain authentication mechanisms) ###

    DEVELOPMENT_API_KEY: str = ''
    """
    This flag should ONLY be set to a non-empty string if this is being run as part of a local development run.
    DO NOT SET THIS OUTSIDE OF A LOCAL SETUP.
    THIS VALUE MUST NOT BE SET IF THIS MICROSERVICE CAN BE ACCESSED BY ANY APPLICATION OUTSIDE OF YOUR CONTROL.

    If this value is set:

    - the application will NOT attempt to create broker users with limited privileges, or implement any kind of message broker Access Control Layer.
    - the application will still configure appropriate queues, etc. for Services and Clients
    - the application will NOT attempt to check that the requested Service is allowed to be associated with this API key, it will just assume it is. This allows people to skip having to manually reserve the Service namespace.
    """

    AUTH_IMPLEMENTATION: Literal['keycloak', 'rudimentary']
    """
    If 'keycloak' : use Keycloak as an auth server
    If 'rudimentary' : use in-memory dictionary as the auth lookup. This is obviously not secure, but can be useful for fast development.
    """

    ### KEYCLOAK SPECIFIC CONFIG ###

    KEYCLOAK_REALM_BASE_URL: HttpUrl
    """
    The root URL for the OIDC provider
    """

    @cached_property
    def keycloak_authorize_url(self) -> str:
        """
        Authentication URL From the OIDC provider.
        """
        return f'{strip_trailing_slash(str(self.KEYCLOAK_REALM_BASE_URL))}/auth'

    @cached_property
    def keycloak_logout_url(self) -> str:
        """
        Authentication URL From the OIDC provider.
        """
        return f'{strip_trailing_slash(str(self.KEYCLOAK_REALM_BASE_URL))}/logout'

    @cached_property
    def keycloak_token_url(self) -> str:
        """
        Token URL From the OIDC provider.
        """
        return f'{strip_trailing_slash(str(self.KEYCLOAK_REALM_BASE_URL))}/token'

    @cached_property
    def keycloak_jwks_url(self) -> str:
        """
        JWKS URL from OIDC provider. Used for token verification.
        """
        return f'{strip_trailing_slash(str(self.KEYCLOAK_REALM_BASE_URL))}/certs'

    SCOPE: str = ''
    """
    Scopes that should be present in token.
    """
    CLIENT_ID: str = ''
    """
    Client ID for this registry service instance from OIDC provider.
    """
    CLIENT_SECRET: str = ''
    """
    Client Secret for this registry service instance from OIDC provider.
    """

    ### SESSION / MISC APP CONFIG ###

    SESSION_SECRET: str = ''
    """
    SECRET to help encryption in authentication flow.
    """
    SESSION_FINGERPRINT_COOKIE: str = ''
    """
    The name of the cookie that will be used to store the user fingerprint.
    """
    SESSION_VERIFY_ID: bool = False
    """Whether to verify the ID token stored in the session cookie on every request.

    If true, it will be checked each request. This means that if the Keycloak server goes down at any time, then the registry service will reject any requests made while the Keycloak server is down.
    """
    SESSION_MAX_AGE: int = 604800
    """
    The max lifetime in seconds of the session cookie.
    """

    SECRET_NAME: Annotated[str, Field(min_length=16)]
    """
    The secret name should NOT be shared with ANYONE. This is for registry service internals, it should not propagate beyond this application.
    """

    ### INTERSECT ###

    SYSTEM_NAME: str = Field(min_length=3, pattern=HIERARCHY_REGEX)
    """
    The System name is used as part of how INTERSECT clients know who to connect to, and can be shared with anyone.
    """

    # TODO - should allow for multiple brokers levels eventually.
    BROKER_HOST: str
    BROKER_PORT: PositiveInt
    BROKER_PROTOCOL: BrokerProtocol
    """The protocol includes version information and will be used directly by Clients"""
    BROKER_APPLICATION: Literal['rabbitmq']
    """The application is strictly a backend mechanism used by the Registry Service to directly talk to specific brokers. It is irrelevant to SDK users."""
    BROKER_TLS_CERT: str | None = None

    # These credentials are for the root broker. Do NOT expose these to clients unless in "DEVELOPMENT" mode. These values should NOT be rotated routinely.
    # TODO - should allow for multiple brokers eventually
    BROKER_ROOT_USERNAME: str
    BROKER_ROOT_PASSWORD: str

    # These are credentials we use for the "least priviliged users", AKA "clients".
    # TODO - should allow for multiple brokers eventually
    # TODO - we should consider rotating these routinely, which would mean that these should NOT be environment variables.
    BROKER_CLIENT_USERNAME: str
    BROKER_CLIENT_PASSWORD: str
    BROKER_CLIENT_API_KEY: str

    # application specific variables, TODO expand on this later
    BROKER_MANAGEMENT_URI: HttpUrl
    """Needs to include scheme, host/port (do NOT include userinfo in the URL), and path - up to where a normal user would login (do not include the RabbitMQ API URL)

    i.e.
    - http://localhost:15672/ for a local setup
    - https://mysubdomain.mydomain.org/proxy_path/ for a production setup where the management API is behind a reverse proxy
    """

    @cached_property
    def broker_client_uri(self) -> str:
        return f'{get_raw_protocol(self.BROKER_PROTOCOL, bool(self.BROKER_TLS_CERT))}://{self.BROKER_CLIENT_USERNAME}:{self.BROKER_CLIENT_PASSWORD}@{self.BROKER_HOST}:{self.BROKER_PORT}{get_uri_path(self.BROKER_PROTOCOL)}'

    ### DATABASE ###

    # advisable to use separate env variables for each, to make deployment engineers' lives easier
    POSTGRESQL_USERNAME: str
    POSTGRESQL_PASSWORD: str
    POSTGRESQL_HOST: str
    POSTGRESQL_PORT: PositiveInt
    POSTGRESQL_DATABASE: str

    @cached_property
    def postgres_url(self) -> str:
        return f'postgresql+psycopg://{self.POSTGRESQL_USERNAME}:{self.POSTGRESQL_PASSWORD}@{self.POSTGRESQL_HOST}:{self.POSTGRESQL_PORT}/{self.POSTGRESQL_DATABASE}'

    ALEMBIC_RUN_MIGRATIONS: bool = True
    """If this is set to True, this assumes that all migrations present are desirable and should be upgraded.

    The only time you would really set this to False would be if you need to manually run `alembic downgrade` and do
    NOT want the latest migrations restored. You would only realistically do this temporarily.
    Also note that the correct way to fix a bad migration is to create a new migration which restores it; in general, you never want to delete migration files.

    It's plausible that we may not be able to autorun migrations ourselves, in which case this can safely be set to False.
    """

    # pydantic config, NOT an environment variable
    model_config = SettingsConfigDict(
        case_sensitive=True,
        frozen=True,
        cli_parse_args=True,
        env_file='.env',  # not used in production; this only needs to exist if you don't have environment variables already set
        extra='ignore',
        validate_default=False,  # I have no idea why pydantic-settings overrides pydantic's default, but we don't need it
        env_ignore_empty=True,  # treat empty ENV strings as None unless the value explicitly defaults to empty string
    )


settings = Settings()

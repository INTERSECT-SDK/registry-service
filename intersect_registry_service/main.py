"""Main file to start backend server."""

import logging
import typing
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi_csrf_protect.exceptions import CsrfProtectError
from sqlmodel import create_engine

from .api import router as api_router
from .auth.csrf import csrf_protect_exception_handler
from .auth.session import IntersectNotAuthenticatedError, handle_unauthenticated
from .core.configuration_manager import ConfigurationManager
from .core.environment import settings
from .core.log_config import configure_logging
from .core.run_migrations import run_migrations
from .middlewares.exceptions import catch_exceptions_middleware
from .ui import router as ui_router

_log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> typing.AsyncGenerator[None, None]:
    # On startup
    _log.info('Initializing app')

    app.state.db = create_engine(
        settings.postgres_url, pool_recycle=3600, echo=settings.LOG_LEVEL == 'DEBUG'
    )
    if settings.ALEMBIC_RUN_MIGRATIONS:
        _log.info('Running migration scripts.')
        run_migrations()
    elif not settings.DEVELOPMENT_API_KEY:
        _log.warning(
            'Skipping migration scripts and verifying connection. Be advised that this should only be a temporary workaround, and that ALEMBIC_RUN_MIGRATIONS should be set to True for general use cases.'
        )
        from sqlmodel import text

        with app.state.db.connect() as connection:
            connection.execute(text('SELECT 1'))
    else:
        _log.warning(
            '!!!IMPORTANT!!!: You are running this in Developer mode. This allows you to quickly connect to a message broker, without having to manually register a Service or handle Service/Client configurations. You should ONLY be doing this if your ENTIRE setup is deployed locally. Do NOT set this flag if you are connecting to a remote broker!'
        )

    _log.info('Configuring broker with initial setup')
    app.state.config_manager = ConfigurationManager(settings)

    _log.info('App initialized')

    yield

    # On cleanup
    _log.info('Shutting down gracefully')

    app.state.db.dispose()

    _log.info('Graceful shutdown complete')


configure_logging(settings)

app = FastAPI(
    debug=True,
    title='INTERSECT Registry Service',
    description='Manage INTERSECT Campaigns and subscribe to messages',
    version=version('intersect-registry-service'),
    redoc_url='/redoc',  # better for end users
    docs_url='/docs',  # this is better for actual developers
    openapi_url='/openapi.json',
    lifespan=lifespan,
)
app.add_exception_handler(IntersectNotAuthenticatedError, handle_unauthenticated)
app.add_exception_handler(CsrfProtectError, csrf_protect_exception_handler)
# make sure this is the LAST exception handler you add
app.add_exception_handler(Exception, catch_exceptions_middleware)

# routes
app.include_router(api_router)
if settings.DEVELOPMENT_API_KEY:
    _log.warning(
        f'DEVELOPMENT_API_KEY has been set to {settings.DEVELOPMENT_API_KEY}. Do NOT set this value in production.'
    )
app.include_router(ui_router)

# mount static files AFTER routes
app.mount('', StaticFiles(directory=(Path(__file__).parent.absolute() / 'ui' / 'static')), 'static')

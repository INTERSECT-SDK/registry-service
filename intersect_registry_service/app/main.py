"""Main file to start backend server."""

import typing
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi_csrf_protect.exceptions import CsrfProtectError
from sqlmodel import create_engine

from .api import router as api_router
from .auth.csrf import csrf_protect_exception_handler
from .auth.session import IntersectNotAuthenticatedError, handle_unauthenticated
from .core.configuration_manager import ConfigurationManager
from .core.environment import settings
from .core.log_config import logger, setup_logging
from .core.run_migrations import run_migrations
from .middlewares.logging_context import add_logging_middleware
from .ui import router as ui_router

# this needs to be called per uvicorn worker
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> typing.AsyncGenerator[None, None]:
    # On startup
    logger.info('Initializing app')

    app.state.db = create_engine(
        settings.postgres_url,
        pool_recycle=3600,
    )
    if settings.ALEMBIC_RUN_MIGRATIONS:
        logger.info('Running migration scripts.')
        run_migrations()
    elif not settings.DEVELOPMENT_API_KEY:
        logger.warning(
            'Skipping migration scripts and verifying connection. Be advised that this should only be a temporary workaround, and that ALEMBIC_RUN_MIGRATIONS should be set to True for general use cases.'
        )
        from sqlmodel import text

        with app.state.db.connect() as connection:
            connection.execute(text('SELECT 1'))

    logger.info('Configuring broker with initial setup')
    app.state.config_manager = ConfigurationManager(settings)

    logger.info('App initialized')

    yield

    # On cleanup
    logger.info('Shutting down gracefully')

    app.state.db.dispose()

    logger.info('Graceful shutdown complete')


app = FastAPI(
    debug=True,
    title='INTERSECT Registry Service',
    description='Manage INTERSECT Campaigns and subscribe to messages',
    version=version('intersect-registry-service'),
    # only provide API documentation for public API URLs. Do not provide documentation for the UI URLs.
    redoc_url='/api/redoc',
    docs_url='/api/docs',
    openapi_url='/api/openapi.json',
    lifespan=lifespan,
)

# Middlewares are executed in REVERSE order from when they are added

add_logging_middleware(app)
app.add_middleware(CorrelationIdMiddleware)

app.add_exception_handler(IntersectNotAuthenticatedError, handle_unauthenticated)
app.add_exception_handler(CsrfProtectError, csrf_protect_exception_handler)

# routes, only the API route has API documentation
app.include_router(api_router)
app.include_router(ui_router)

# mount static files AFTER routes
app.mount('', StaticFiles(directory=(Path(__file__).parent.absolute() / 'ui' / 'static')), 'static')

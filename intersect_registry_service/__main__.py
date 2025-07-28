import structlog
import uvicorn

from intersect_registry_service.app.core.configuration_manager import ConfigurationManager
from intersect_registry_service.app.core.environment import settings
from intersect_registry_service.app.core.log_config import setup_logging
from intersect_registry_service.app.core.run_migrations import run_migrations

logger = structlog.stdlib.get_logger('intersect-registry-service.main')


def main() -> None:
    # WARNING - the logger names will NOT propogate to workers if uvicorn.reload = True or uvicorn.server_workers > 1
    # so we should setup logging twice - once on the uvicorn main, and once in the runner
    setup_logging()

    host = '0.0.0.0' if settings.PRODUCTION else '127.0.0.1'  # noqa: S104 (mandatory if running in Docker)
    url = f'http://{host}:{settings.SERVER_PORT}{settings.BASE_URL}'
    if settings.PRODUCTION:
        logger.info('Running server at %s', url)
    else:
        reload_str = ', server will reload on file changes' if settings.SERVER_WORKERS == 1 else ''
        logger.info('Running DEVELOPMENT server at %s%s', url, reload_str)
        logger.info('View docs at %s/api/docs', url)

    if settings.DEVELOPMENT_API_KEY:
        logger.warning(
            'WARNING: DEVELOPMENT_API_KEY was set to a non-empty value, running in Developer Mode. Do NOT use this on a remote server.'
        )

    if settings.AUTH_IMPLEMENTATION == 'rudimentary':
        logger.warning(
            'WARNING: Auth implementation is "rudimentary", make sure you use another value in production'
        )
    else:
        logger.info('Using keycloak as auth implementation')

    # initialize backing services
    if settings.ALEMBIC_RUN_MIGRATIONS:
        logger.info('Running migration scripts.')
        run_migrations()

    # TODO remove this block once we start initializing this directly on the brokers
    config_manager = ConfigurationManager(settings)
    config_manager.initialize_broker(settings)

    uvicorn.run(
        'intersect_registry_service.app.main:app',
        host=host,
        port=settings.SERVER_PORT,
        reload=(not settings.PRODUCTION and settings.SERVER_WORKERS == 1),
        workers=settings.SERVER_WORKERS,
        root_path=settings.BASE_URL,
        proxy_headers=settings.PRODUCTION,
        forwarded_allow_ips='*'
        if settings.PRODUCTION
        else '127.0.0.1',  # This assumes that you will always
        server_header=False,
        # override Uvicorn's loggers with our own, and disable the uvicorn access logger
        log_config=None,
        access_log=False,
    )


if __name__ == '__main__':
    main()

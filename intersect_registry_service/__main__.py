import structlog
import uvicorn

from intersect_registry_service.app.core.environment import settings
from intersect_registry_service.app.core.log_config import setup_logging

logger = structlog.stdlib.get_logger('intersect-registry-service.main')


def main() -> None:
    # WARNING - the logger names will NOT propogate to workers if uvicorn.reload = True
    setup_logging()

    host = '0.0.0.0' if settings.PRODUCTION else '127.0.0.1'  # noqa: S104 (mandatory if running in Docker)
    url = f'http://{host}:{settings.SERVER_PORT}{settings.BASE_URL}'
    if settings.PRODUCTION:
        logger.info('Running server at %s', url)
    else:
        logger.info('Running DEVELOPMENT server at %s, server will reload on file changes', url)
        logger.info('View docs at %s/docs', url)

    if settings.DEVELOPMENT_API_KEY:
        logger.warning(
            'WARNING: DEVELOPMENT_API_KEY was set to a non-empty value, running in Developer Mode. Do NOT use this on a remote server.'
        )

    uvicorn.run(
        'intersect_registry_service.app.main:app',
        host=host,
        port=settings.SERVER_PORT,
        reload=(not settings.PRODUCTION and settings.SERVER_WORKERS == 1),
        workers=settings.SERVER_WORKERS,
        root_path=settings.BASE_URL,
        server_header=False,
        # override Uvicorn's loggers with our own, and disable the uvicorn access logger
        log_config=None,
        access_log=False,
    )


if __name__ == '__main__':
    main()

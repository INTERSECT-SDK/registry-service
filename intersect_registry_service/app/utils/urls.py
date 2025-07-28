from typing import Any

from fastapi import Request
from starlette.datastructures import URL

from ..core.environment import settings
from ..core.log_config import logger


def url_abspath_for(
    request: Request, name: str, query_params: dict[str, str] | None = None, /, **path_params: Any
) -> str:
    """This returns the PATH, the QUERY, and the FRAGMENT of the output for 'request.url_for'. It's useful for the application linking to itself, for a few reasons:

    Params:
      - name = name of route
      - query_params = dictionary of query keys to query values, leave empty if no query
      - path_params = kwargs which normally get passed into url_for

    1. If behind a proxy, this allows you to guarantee the correct path, without having to rely on X-Forwarded-Proto and X-Forwarded-Host
    2. Even if not behind a proxy, this still skips the DNS check

    You need to set uvicorn's --root-path to generate valid API documentation, but this will ruin url_for if you are behind a reverse proxy.
    """
    url_for = request.url_for(name, **path_params)
    if query_params:
        url_for.include_query_params(**query_params)
    url_str = str(url_for)
    path_position = url_str.find(
        '/', 8
    )  # skip evaluating scheme ("https://"), would only fail for ws://aa/path or shorter
    return url_str[path_position:]


def absolute_url_for(request: Request, name: str) -> URL | None:
    """Get the absolute URL of the endpoint from 'name'. This is needed for external services, i.e. Keycloak, to call back into the app.

    This is a little less reliable than url_abspath_for because it relies on your proxy headers being set correctly. As such, we return "None" if we can tell that the proxy headers are wrong.

    This also may not work well if you have to travel between two or more proxies to actually reach the website.
    """
    url_for = request.url_for(name)
    if not settings.PRODUCTION:
        return url_for
    forwarded_proto = request.headers.get('X-Forwarded-Proto')
    forwarded_host = request.headers.get('X-Forwarded-Host')
    if not forwarded_proto or not forwarded_host:
        # You can ignore this if you are not actually behind a proxy, otherwise you should assume this is a misconfiguration on your proxy's end
        logger.error(
            'Proxy did not set both X-Forwarded-Proto and X-Forwarded-Host. X-Forwarded-Proto value = %s X-Forwarded-Host value = %s'
        )
        return None
    return URL(
        scheme=forwarded_proto or url_for.scheme,
        netloc=forwarded_host or url_for.netloc,
        path=url_for.path,
    )

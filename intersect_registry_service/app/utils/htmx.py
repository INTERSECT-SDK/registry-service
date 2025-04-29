"""Some HTMX utility functions

We mostly only care about the headers on the backend: https://htmx.org/reference/#headers

On the frontend, you should almost always use the HTML attributes unless you're writing something fairly complex.
"""

from fastapi import Request


def is_htmx_request(request: Request) -> bool:
    """If this returns True, the user has Javascript enabled and is also using HTMX; if False, they don't."""
    return bool(request.headers.get('HX-Request'))

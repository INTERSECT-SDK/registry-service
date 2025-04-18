"""Some HTMX utility functions

We mostly only care about the headers: https://htmx.org/reference/#headers
"""

from fastapi import Request


def is_htmx_request(request: Request) -> bool:
    """If this returns True, the user has Javascript enabled; if False, they don't."""
    return bool(request.headers.get('HX-Request'))

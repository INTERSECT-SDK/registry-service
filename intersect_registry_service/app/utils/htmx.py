"""Some HTMX utility functions

We mostly only care about the headers on the backend: https://htmx.org/reference/#headers

On the frontend, you should almost always use the HTML attributes unless you're writing something fairly complex.
"""

from fastapi import Request, Response
from fastapi.responses import RedirectResponse


def is_htmx_request(request: Request) -> bool:
    """If this returns True, the user has Javascript enabled and is also using HTMX; if False, they don't."""
    return bool(request.headers.get('HX-Request'))


def do_universal_redirect(request: Request, redirect_uri: str) -> Response:
    """Use this function when you need to force HTMX to do the Post-Redirect-Get pattern. Mostly used for logouts (especially CSRF invalidation)"""
    if is_htmx_request(request):
        headers = {'HX-Redirect': redirect_uri, 'HX-Refresh': 'true'}
        # 204 is the HTMX response which is both not a swap and not an error
        return Response(status_code=204, headers=headers)

    return RedirectResponse(redirect_uri, status_code=303)

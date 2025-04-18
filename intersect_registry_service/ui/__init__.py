"""UI definitions

These endpoints are meant to be accessed by users accessing the website in the browser.
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from .endpoints.login import router as login_router
from .endpoints.microservice_user import router as user_router

router = APIRouter(tags=['UI'])
router.include_router(login_router)
router.include_router(user_router)


@router.get('/robots.txt')
def robots() -> PlainTextResponse:
    """Discourage good-faith scrapers and do not reveal any information to bad-faith scrapers."""
    return PlainTextResponse("""
User-Agent: *
Disallow: /
""")

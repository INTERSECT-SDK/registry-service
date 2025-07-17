"""UI definitions

These endpoints are meant to be accessed by users accessing the website in the browser.
"""

from fastapi import APIRouter

from ..core.environment import settings
from .endpoints.microservice_user import router as user_router

router = APIRouter(include_in_schema=False)
if settings.AUTH_IMPLEMENTATION == 'keycloak':
    from .endpoints.login_keycloak import router as login_router

    router.include_router(login_router)
elif settings.AUTH_IMPLEMENTATION == 'rudimentary':
    from .endpoints.login_rudimentary import router as login_router

    router.include_router(login_router)
router.include_router(user_router)

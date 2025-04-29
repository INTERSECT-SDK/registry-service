"""UI definitions

These endpoints are meant to be accessed by users accessing the website in the browser.
"""

from fastapi import APIRouter

from .endpoints.login import router as login_router
from .endpoints.microservice_user import router as user_router

router = APIRouter(include_in_schema=False)
router.include_router(login_router)
router.include_router(user_router)

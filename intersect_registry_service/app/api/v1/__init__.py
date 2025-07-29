from fastapi import APIRouter

from ...core.environment import settings
from .endpoints import general

router = APIRouter(prefix='/v1', tags=['V1'])
router.include_router(general.router)
if settings.DEVELOPMENT_API_KEY:
    from .endpoints.sdk import impl_devmode as sdk
else:
    from .endpoints.sdk import impl_real as sdk  # type: ignore[no-redef]
router.include_router(sdk.router, prefix='/sdk', tags=['SDK'])

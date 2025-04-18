from fastapi import APIRouter

from .endpoints import general, sdk

router = APIRouter(prefix='/v1')
# router.include_router(credentials.router, prefix='/credentials', tags=['Credentials'])
router.include_router(general.router)
router.include_router(sdk.router, prefix='/sdk', tags=['SDK'])

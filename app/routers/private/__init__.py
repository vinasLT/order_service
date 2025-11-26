from fastapi import APIRouter

from app.routers.private.v1 import router as v1_router

private_router = APIRouter(prefix="/private")
private_router.include_router(v1_router)

__all__ = ["private_router"]

from fastapi import APIRouter

from app.routers.private import private_router

api_router = APIRouter()
api_router.include_router(private_router)

__all__ = ["api_router"]

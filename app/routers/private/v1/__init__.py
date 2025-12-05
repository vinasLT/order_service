from fastapi import APIRouter

from app.routers.private.v1 import orders

router = APIRouter(prefix="/v1")
router.include_router(orders.order_router)

__all__ = ["router"]

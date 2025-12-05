from fastapi import APIRouter

from app.routers.private.v1 import orders, invoice

router = APIRouter(prefix="/v1")
router.include_router(orders.order_router)
router.include_router(invoice.invoice_router)

__all__ = ["router"]

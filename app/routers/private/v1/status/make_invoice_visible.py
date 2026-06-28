from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Depends
from rfc9457 import BadRequestProblem

from app.config import Permissions
from app.database.schemas import OrderRead

make_invoice_visible_router = APIRouter(
    prefix="/{order_id}/make-invoice-visible",
    tags=["Status"],
)


@make_invoice_visible_router.post(
    "",
    response_model=OrderRead,
    description=f"Make invoice visible for user who own order, required permission: {Permissions.ORDER_ALL_WRITE.value}",
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def make_invoice_visible_invoice_visible(order_id: int):
    raise BadRequestProblem(detail="Use auction invoice upload flow")

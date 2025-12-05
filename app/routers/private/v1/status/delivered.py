from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Depends
from rfc9457 import BadRequestProblem, NotFoundProblem
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Permissions
from app.database.crud import OrderService
from app.database.db.session import get_async_db
from app.database.schemas import OrderRead, OrderUpdate
from app.enums.order import OrderStatusEnum

delivered_router = APIRouter(
    prefix="/{order_id}/delivered",
    tags=["Status"],
)


@delivered_router.post(
    "",
    response_model=OrderRead,
    description=f"Set order status to delivered, required permission: {Permissions.ORDER_ALL_WRITE.value}",
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def set_delivered(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    order = await order_service.get(order_id)
    if not order:
        raise NotFoundProblem(detail="Order not found")

    if order.delivery_status != OrderStatusEnum.CUSTOM_INVOICE_ADDED:
        raise BadRequestProblem(
            detail=f"You cannot change status because it is not {OrderStatusEnum.CUSTOM_INVOICE_ADDED.value}"
        )

    # TODO: add notification to user

    return await order_service.update(
        order_id,
        OrderUpdate(delivery_status=OrderStatusEnum.DELIVERED),
    )

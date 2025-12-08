from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Depends
from rfc9457 import NotFoundProblem, BadRequestProblem
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Permissions
from app.database.crud import OrderService
from app.database.db.session import get_async_db
from app.database.schemas import OrderRead, OrderUpdate
from app.enums.order import OrderStatusEnum
from app.routers.private.v1.status.get_order_mixin import get_order_with_check
from app.services.send_notification import send_status_change_notifications

make_invoice_visible_router = APIRouter(
    prefix="/{order_id}/make-invoice-visible",
    tags=["Status"],
)


@make_invoice_visible_router.post(
    '',
    response_model=OrderRead,
    description=f"Make invoice visible for user who own order, required permission: {Permissions.ORDER_ALL_WRITE.value}",
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def make_invoice_visible_invoice_visible(
        order_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    order_service = OrderService(db)


    order = await get_order_with_check(order_id, order_service, OrderStatusEnum.PORT_CHOSEN)
    previous_status = order.delivery_status

    updated_order = await order_service.update(order_id, OrderUpdate(delivery_status=OrderStatusEnum.INVOICE_ADDED))

    await send_status_change_notifications(updated_order, previous_status, order.user_uuid)

    return updated_order

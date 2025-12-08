from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Depends
from rfc9457 import BadRequestProblem
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Permissions
from app.core.logger import logger
from app.database.crud import CustomInvoiceService, OrderService
from app.database.db.session import get_async_db
from app.database.schemas import OrderRead, OrderUpdate
from app.enums.custom_invoice_status import CustomInvoiceStatus
from app.enums.order import OrderStatusEnum
from app.routers.private.v1.status.get_order_mixin import get_order_with_check
from app.rpc_client.auth import AuthRpcClient
from app.services.send_notification import send_status_change_notifications

custom_invoice_added_router = APIRouter(
    prefix="/{order_id}/custom-invoice-added",
    tags=["Status"],
)


@custom_invoice_added_router.post(
    "",
    response_model=OrderRead,
    description=f"Set order status to custom invoice added, required permission: {Permissions.ORDER_ALL_WRITE.value}",
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def set_custom_invoice_added(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    custom_invoice_service = CustomInvoiceService(db)

    order = await get_order_with_check(order_id, order_service, OrderStatusEnum.VEHICLE_IN_CUSTOM_AGENCY)

    custom_invoice = await custom_invoice_service.get_by_order_id(order_id)
    if not custom_invoice:
        raise BadRequestProblem(detail="Custom invoice file is not requested or uploaded yet")

    if custom_invoice.status != CustomInvoiceStatus.AVAILABLE:
        raise BadRequestProblem(detail="Custom invoice file is not uploaded yet")

    previous_status = order.delivery_status
    updated_order = await order_service.update(
        order_id,
        OrderUpdate(delivery_status=OrderStatusEnum.CUSTOM_INVOICE_ADDED),
    )

    await send_status_change_notifications(updated_order, previous_status, order.user_uuid)

    return updated_order

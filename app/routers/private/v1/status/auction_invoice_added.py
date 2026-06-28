from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Depends
from rfc9457 import BadRequestProblem
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Permissions
from app.database.crud import AuctionInvoiceService, OrderService
from app.database.db.session import get_async_db
from app.database.schemas import OrderRead, OrderUpdate
from app.enums.custom_invoice_status import FileInvoiceStatus
from app.enums.order import OrderStatusEnum
from app.routers.private.v1.status.get_order_mixin import get_order_with_check
from app.services.send_notification import send_status_change_notifications

auction_invoice_added_router = APIRouter(
    prefix="/{order_id}/auction-invoice",
    tags=["Status"],
)


@auction_invoice_added_router.post(
    "",
    response_model=OrderRead,
    description=(
        f"Set order status to invoice added after auction invoice upload, "
        f"required permission: {Permissions.ORDER_ALL_WRITE.value}"
    ),
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def set_auction_invoice_added(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    auction_invoice_service = AuctionInvoiceService(db)

    order = await get_order_with_check(order_id, order_service, OrderStatusEnum.PORT_CHOSEN)

    auction_invoice = await auction_invoice_service.get_by_order_id(order_id)
    if not auction_invoice:
        raise BadRequestProblem(detail="Auction invoice file is not requested or uploaded yet")

    if auction_invoice.status != FileInvoiceStatus.AVAILABLE:
        raise BadRequestProblem(detail="Auction invoice file is not uploaded yet")

    previous_status = order.delivery_status
    updated_order = await order_service.update(
        order_id,
        OrderUpdate(delivery_status=OrderStatusEnum.INVOICE_ADDED),
    )

    await send_status_change_notifications(updated_order, previous_status, order.user_uuid)

    return updated_order

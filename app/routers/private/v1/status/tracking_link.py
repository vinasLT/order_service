from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel, Field
from rfc9457 import BadRequestProblem, NotFoundProblem
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Permissions
from app.database.crud import OrderService
from app.database.db.session import get_async_db
from app.database.schemas import OrderRead, OrderUpdate
from app.enums.order import OrderStatusEnum

tracking_link_router = APIRouter(
    prefix="/{order_id}/tracking-link",
    tags=["Status"],
)


class TrackingLinkIn(BaseModel):
    tracking_link: str = Field(..., min_length=1, description="Tracking link for the order")


@tracking_link_router.post(
    "",
    response_model=OrderRead,
    description=f"Add tracking link to order, required permission: {Permissions.ORDER_ALL_WRITE.value}",
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def add_tracking_link(
    order_id: int,
    data: TrackingLinkIn = Body(...),
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    order = await order_service.get(order_id)
    if not order:
        raise NotFoundProblem(detail="Order not found")

    if order.delivery_status not in [OrderStatusEnum.INVOICE_ADDED, OrderStatusEnum.TRACKING_ADDED]:
        raise BadRequestProblem(
            detail=(
                f"You cannot change status because it is not "
                f"{OrderStatusEnum.INVOICE_ADDED.value} or {OrderStatusEnum.TRACKING_ADDED.value}"
            )
        )

    # TODO: add notification to user


    return await order_service.update(
        order_id,
        OrderUpdate(
            tracking_link=data.tracking_link,
            delivery_status=OrderStatusEnum.TRACKING_ADDED,
        ),
    )

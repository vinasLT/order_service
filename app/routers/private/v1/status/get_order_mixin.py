from rfc9457 import NotFoundProblem, BadRequestProblem

from app.database.crud import OrderService
from app.database.models import Order
from app.database.schemas import OrderUpdate
from app.enums.order import OrderStatusEnum
from app.services.send_notification import send_status_change_notifications


async def get_order_with_check(
    order_id: int,
    order_service: OrderService,
    previous_status: OrderStatusEnum | tuple[OrderStatusEnum, ...],
) -> Order:
    order = await order_service.get(order_id)
    if not order:
        raise NotFoundProblem(detail="Order not found")

    allowed_statuses = (
        (previous_status,) if isinstance(previous_status, OrderStatusEnum) else tuple(previous_status)
    )

    if order.delivery_status not in allowed_statuses:
        allowed_display = " or ".join(status.value for status in allowed_statuses)
        raise BadRequestProblem(detail=f"You cannot change status because it is not {allowed_display}")

    return order


async def update_status_with_notifications(
    order_id: int,
    order_service: OrderService,
    previous_status: OrderStatusEnum | tuple[OrderStatusEnum, ...],
    new_status: OrderStatusEnum,
) -> Order:
    order = await get_order_with_check(order_id, order_service, previous_status)
    previous_delivery_status = order.delivery_status

    updated_order = await order_service.update(order_id, OrderUpdate(delivery_status=new_status))

    await send_status_change_notifications(updated_order, previous_delivery_status, order.user_uuid)

    return updated_order

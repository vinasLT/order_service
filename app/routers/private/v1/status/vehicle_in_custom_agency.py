from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Permissions
from app.database.crud import OrderService
from app.database.db.session import get_async_db
from app.database.schemas import OrderRead
from app.enums.order import OrderStatusEnum
from app.routers.private.v1.status.get_order_mixin import update_status_with_notifications

vehicle_in_custom_agency_router = APIRouter(
    prefix="/{order_id}/vehicle-in-custom-agency",
    tags=["Status"],
)


@vehicle_in_custom_agency_router.post(
    "",
    response_model=OrderRead,
    description=f"Set order status to vehicle in custom agency, required permission: {Permissions.ORDER_ALL_WRITE.value}",
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def set_vehicle_in_custom_agency(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)

    return await update_status_with_notifications(
        order_id,
        order_service,
        OrderStatusEnum.TRACKING_ADDED,
        OrderStatusEnum.VEHICLE_IN_CUSTOM_AGENCY,
    )

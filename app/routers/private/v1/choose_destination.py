from AuthTools import HeaderUser
from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Depends, Body
from rfc9457 import ForbiddenProblem, NotFoundProblem, BadRequestProblem
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import Permissions
from app.core.logger import logger
from app.database.crud import OrderService
from app.database.db.session import get_async_db
from app.database.schemas import OrderRead, OrderUpdate
from app.enums.order import OrderStatusEnum
from app.schemas.destination import DestinationOut
from app.services.create_order_from_lot import GenerateFromLot
from app.services.send_notification import send_status_change_notifications
from app.rpc_client.auth import AuthRpcClient
from app.services.rabbit_service.service import RabbitMQPublisher

choose_destination_router = APIRouter()

@choose_destination_router.post("/{order_id}/choose-destination",
                            description="Status 1, user must choose terminal to continue\n"
                                        f"required permissions: {Permissions.ORDER_OWN_WRITE.value}",
                            response_model=OrderRead)
async def choose_destination(
        order_id: int,
        destination_id: int = Body(...),
        db: AsyncSession = Depends(get_async_db),
        user: HeaderUser = Depends(require_permissions(Permissions.ORDER_OWN_WRITE))
):
    order_service = OrderService(db)
    order = await order_service.get(order_id)

    if order.delivery_status not in [OrderStatusEnum.WON, OrderStatusEnum.PORT_CHOSEN]:
        raise BadRequestProblem(detail="You cannot change destination after invoice added")


    if order.user_uuid != user.uuid:
        raise ForbiddenProblem(detail="Not allowed")

    calculator = await GenerateFromLot.get_calculator_from_order(order)
    detailed_data = calculator.detailed_data
    destinations_mapped = {}
    for destination in detailed_data.available_destinations:
        destinations_mapped[destination.destination_id] = destination.destination_name

    if destination_id not in destinations_mapped.keys():
        raise NotFoundProblem(detail=f"Destination id {destination_id} not found")

    destination_name = destinations_mapped[destination_id]

    previous_status = order.delivery_status
    previous_destination_id = order.destination_id

    updated_order = await order_service.update(
        order_id,
        OrderUpdate(
            destination_id=destination_id,
            destination_name=destination_name,
            delivery_status=OrderStatusEnum.PORT_CHOSEN
        )
    )

    if not previous_destination_id:

        invoice_items = GenerateFromLot.build_invoice_items_from_order_data(
            order=order,
            default_calculator=calculator.data.calculator,
        )

        await order_service.create_invoice_items_batch(order_id, invoice_items)

        await send_status_change_notifications(
            updated_order,
            previous_status,
            user_uuid=user.uuid,
            is_telegram=True,
        )

    return updated_order



@choose_destination_router.get(
    "/{order_id}/available-destinations",
    response_model=list[DestinationOut],
    description="Get available destinations to choose from\n"
                f"Required permissions: {Permissions.ORDER_OWN_READ.value}",
)
async def available_destinations(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    user: HeaderUser = Depends(require_permissions(Permissions.ORDER_OWN_READ))
):
    order_service = OrderService(db)
    order = await order_service.get(order_id)
    if order.user_uuid != user.uuid:
        raise ForbiddenProblem(detail="Not allowed")
    calculator = await GenerateFromLot.get_calculator_from_order(order)
    detailed_data = calculator.detailed_data

    destinations = []
    for destination in detailed_data.available_destinations:
        destinations.append(DestinationOut(
            destination_id=destination.destination_id,
            destination_name=destination.destination_name,
        ))

    return destinations






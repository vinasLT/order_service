from app.core.logger import logger
from app.enums.order import OrderStatusEnum
from app.rpc_client.auth import AuthRpcClient
from app.services.rabbit_service.service import RabbitMQPublisher


async def send_status_change_notifications(
    updated_order,
    previous_status: OrderStatusEnum,
    user_uuid: str,
    is_telegram: bool = False
):
    human_readable_statuses = {
        OrderStatusEnum.WON: "Bid won",
        OrderStatusEnum.PORT_CHOSEN: "Port chosen",
        OrderStatusEnum.INVOICE_ADDED: "Invoice added",
        OrderStatusEnum.TRACKING_ADDED: "Tracking added",
        OrderStatusEnum.VEHICLE_IN_CUSTOM_AGENCY: "Vehicle in custom agency",
        OrderStatusEnum.CUSTOM_INVOICE_ADDED: "Custom invoice added",
        OrderStatusEnum.DELIVERED: "Delivered",
    }

    def human_status(status: OrderStatusEnum) -> str:
        return human_readable_statuses.get(status, status.value)

    user_email = ""
    user_phone = ""
    user = None
    try:
        async with AuthRpcClient() as auth_client:
            user = await auth_client.get_user(user_uuid=user_uuid)
            user_email = user.email or ""
            user_phone = user.phone_number or ""
    except Exception as exc:
        logger.error(
            "Failed to fetch user info for status change notification",
            extra={"user_uuid": user_uuid, "error": str(exc)},
        )

    base_payload = {
        'user_uuid': user_uuid,
        "new_order_status": updated_order.delivery_status.value,
        "previous_order_status": previous_status.value,
        "new_order_status_human": human_status(updated_order.delivery_status),
        "previous_order_status_human": human_status(previous_status),
        "order_id": updated_order.id,
        "vin": updated_order.vin,
        "vehicle_title": updated_order.vehicle_name,
        "auction": updated_order.auction.value if updated_order.auction else None,
        "lot_id": updated_order.lot_id,
        "email": user_email,
        "phone_number": user_phone,
    }

    publisher = RabbitMQPublisher()
    try:
        if is_telegram:
            base_payload["destination"] = "telegram"
            base_payload['user_email'] = user_email
            base_payload['user_phone'] = user_phone
            base_payload['user_name'] = user.first_name + " " + user.last_name
            await publisher.publish(
                routing_key="order.status_updated",
                payload=base_payload,
            )
        else:
            for destination in ("email", "sms"):
                payload = base_payload | {"destination": destination}
                await publisher.publish(
                    routing_key="order.status_updated",
                    payload=payload,
                )
    except Exception as exc:
        logger.error(
            "Failed to publish order status update notification",
            extra={
                "order_id": updated_order.id,
                "routing_key": "order.status_updated",
                "error": str(exc),
            },
        )
    finally:
        await publisher.close()

import json

from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.logger import logger
from app.database.crud import CustomInvoiceService, OrderService
from app.database.schemas import CustomInvoiceUpdate
from app.enums.auction import AuctionEnum
from app.enums.custom_invoice_status import CustomInvoiceStatus
from app.services.create_order_from_lot import GenerateFromLot
from app.services.rabbit_service.base import RabbitBaseService
from app.services.rabbit_service.file_routing_keys import RoutingKeys


class OrderRabbitConsumer(RabbitBaseService):
    def __init__(self, db_session_factory: async_sessionmaker[AsyncSession], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_session_factory = db_session_factory


    async def process_message(self, message: AbstractIncomingMessage):
        message_data = message.body.decode("utf-8")
        payload = json.loads(message_data).get("payload")
        routing_key = message.routing_key

        logger.info("Received new message", extra={"payload": payload})


        if routing_key == RoutingKeys.FILES_UPLOADED:

            async with self.db_session_factory() as session:
                logger.info("Processing message", extra={"routing_key": routing_key})

                custom_invoice_service = CustomInvoiceService(session)
                custom_invoice = await custom_invoice_service.get_by_file_id(payload.get("id"))
                if custom_invoice:
                    status = payload.get("status", "").upper()
                    if status == "AVAILABLE":
                        logger.info("Invoice is available", extra={"invoice_id": custom_invoice.id})
                        await custom_invoice_service.update(custom_invoice.id,  CustomInvoiceUpdate(status=CustomInvoiceStatus.AVAILABLE))
                    elif status == "FAILED":
                        logger.info("Invoice is failed", extra={"invoice_id": custom_invoice.id})
                        await custom_invoice_service.delete(custom_invoice.id)
                    else:
                        logger.warning("Unprocessable status received", extra={"status": status})
        elif routing_key == RoutingKeys.BID_WON:
            logger.info("Bid won received")
            user_uuid = payload.get("user_uuid")
            auction = payload.get("auction")

            lot_id = payload.get("lot_id")
            bid_amount = payload.get("bid_amount")
            async with self.db_session_factory() as session:
                order_service = OrderService(session)
                if await order_service.exists_by_lot_id(lot_id):
                    logger.info(
                        "Order already exists for lot, skipping duplicate bid won",
                        extra={"lot_id": lot_id, "user_uuid": user_uuid},
                    )
                    return
            try:
                auction_enum = AuctionEnum(auction.upper() if auction else "UNKNOWN")
            except Exception:
                logger.exception(
                    "Unknown auction site for bid won",
                    extra={"auction_site": auction, "payload": payload},
                )
                return

            try:
                generator = GenerateFromLot(
                    lot_id=lot_id,
                    auction=auction_enum,
                    user_uuid=user_uuid,
                    bid_amount=bid_amount,
                )
                await generator.generate()
            except IntegrityError:
                logger.info(
                    "Order already exists (db constraint), skipping duplicate bid won",
                    extra={"lot_id": lot_id, "auction": auction, "user_uuid": user_uuid},
                )
            except Exception as exc:
                logger.exception(
                    "Error processing bid won",
                    extra={
                        "error": str(exc),
                        "lot_id": lot_id,
                        "auction": auction_enum.value if 'auction_enum' in locals() else auction,
                        "user_uuid": user_uuid,
                    },
                )




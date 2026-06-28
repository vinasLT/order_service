from io import BytesIO

import grpc
import grpc.aio
from AuthTools import HeaderUser
from AuthTools.Permissions.dependencies import require_one_of_permissions
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse, StreamingResponse
from rfc9457 import ForbiddenProblem, NotFoundProblem, BadRequestProblem
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Permissions
from app.core.logger import logger
from app.core.utils import uses_legacy_generated_invoice
from app.database.crud import AuctionInvoiceService, OrderService
from app.database.db.session import get_async_db
from app.database.models import Order
from app.enums.custom_invoice_status import FileInvoiceStatus
from app.enums.order import OrderStatusEnum
from app.rpc_client.auth import AuthRpcClient
from app.rpc_client.calculator import DetailedInfoService
from app.rpc_client.files import FilesRpcClient
from app.services.invoice_generator.generator import InvoiceGenerator


invoice_router = APIRouter(prefix="/{order_id}/invoice", tags=["Invoice"])


async def _get_usd_to_eur_rate(order: Order) -> float | None:
    try:
        async with DetailedInfoService() as calculator_client:
            rate = await calculator_client.get_rate()
    except grpc.aio.AioRpcError:
        logger.warning(
            "Calculator RPC failed while fetching USD/EUR rate",
            extra={"order_id": order.id},
        )
        return None
    if rate:
        logger.info(
            "USD/EUR rate resolved for invoice",
            extra={"order_id": order.id, "usd_to_eur_rate": rate},
        )
    else:
        logger.warning(
            "USD/EUR rate not available for invoice",
            extra={"order_id": order.id},
        )
    return rate


@invoice_router.get(
    "",
    description=(
        f"Get invoice PDF for order (uploaded auction invoice or legacy generated PDF). "
        f"Required permissions: {Permissions.ORDER_OWN_READ.value} (owner) or "
        f"{Permissions.ORDER_ALL_READ.value} (admin)"
    ),
)
async def get_invoice(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    user: HeaderUser = Depends(require_one_of_permissions(Permissions.ORDER_OWN_READ, Permissions.ORDER_ALL_READ)),
):
    logger.info(
        "Invoice request received",
        extra={"order_id": order_id, "user_uuid": user.uuid},
    )
    order_service = OrderService(db)
    order = await order_service.get(order_id)
    if not order:
        raise NotFoundProblem(detail="Order not found")

    has_all_orders_permission = Permissions.ORDER_ALL_READ.value in user.permissions
    is_order_owner = order.user_uuid == user.uuid

    if not has_all_orders_permission and not is_order_owner:
        raise ForbiddenProblem(detail="Not allowed")

    if order.delivery_status == OrderStatusEnum.WON:
        detail = (
            f"You need wait until status of order will be: {OrderStatusEnum.PORT_CHOSEN.value}"
            if has_all_orders_permission
            else "You need to choose port to see invoice"
        )
        raise BadRequestProblem(detail=detail)

    if order.delivery_status == OrderStatusEnum.PORT_CHOSEN and not has_all_orders_permission:
        raise BadRequestProblem(detail=f"You need wait until status of order will be: {OrderStatusEnum.INVOICE_ADDED.value}")

    logger.info(
        "Invoice request passed access/status checks",
        extra={"order_id": order.id, "delivery_status": order.delivery_status},
    )

    auction_invoice_service = AuctionInvoiceService(db)
    auction_invoice = await auction_invoice_service.get_by_order_id(order_id)

    if auction_invoice and auction_invoice.status == FileInvoiceStatus.AVAILABLE:
        try:
            async with FilesRpcClient() as client:
                download = await client.get_download_url(file_id=auction_invoice.file_id)
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundProblem(detail="Invoice file not found")
            raise BadRequestProblem(detail=e.details())
        return RedirectResponse(url=download.download_url)

    if not uses_legacy_generated_invoice(order.delivery_status, auction_invoice is not None):
        raise BadRequestProblem(detail="Upload auction invoice to make it available")

    auth_user = None
    try:
        async with AuthRpcClient() as auth_client:
            auth_user = await auth_client.get_user(user_uuid=order.user_uuid)
    except grpc.aio.AioRpcError:
        # Ignore RPC failures to avoid blocking invoice generation
        pass

    usd_to_eur_rate = await _get_usd_to_eur_rate(order)
    generator = InvoiceGenerator(order, user=auth_user, usd_to_eur_rate=usd_to_eur_rate)
    pdf_bytes = generator.generate_invoice_based_on_invoice_type()

    filename = f"invoice_{order.vin}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'},
    )

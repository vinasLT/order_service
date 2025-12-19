from io import BytesIO

import grpc.aio
from AuthTools import HeaderUser
from AuthTools.Permissions.dependencies import require_one_of_permissions
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from rfc9457 import ForbiddenProblem, NotFoundProblem, BadRequestProblem
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Permissions
from app.database.crud import OrderService
from app.database.db.session import get_async_db
from app.enums.order import OrderStatusEnum
from app.rpc_client.auth import AuthRpcClient
from app.services.invoice_generator.generator import InvoiceGenerator


invoice_router = APIRouter(prefix="/{order_id}/invoice", tags=["Invoice"])


@invoice_router.get(
    "",
    description=f"Get invoice PDF for order\nRequired permissions: {Permissions.ORDER_OWN_READ.value}(for user)\n"
                f"{Permissions.ORDER_ALL_READ.value}(for admin)",
)
async def get_invoice(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    user: HeaderUser = Depends(require_one_of_permissions(Permissions.ORDER_OWN_READ, Permissions.ORDER_ALL_READ)),
):
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

    auth_user = None
    try:
        async with AuthRpcClient() as auth_client:
            auth_user = await auth_client.get_user(user_uuid=order.user_uuid)
    except grpc.aio.AioRpcError:
        # Ignore RPC failures to avoid blocking invoice generation
        pass

    generator = InvoiceGenerator(order, user=auth_user)
    pdf_bytes = generator.generate_invoice_based_on_invoice_type()

    filename = f"invoice_{order.vin}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'},
    )

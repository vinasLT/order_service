from io import BytesIO

from AuthTools import HeaderUser
from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from rfc9457 import ForbiddenProblem, NotFoundProblem
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Permissions
from app.database.crud import OrderService
from app.database.db.session import get_async_db
from app.services.invoice_generator.generator import InvoiceGenerator


invoice_router = APIRouter(prefix="/invoice", tags=["Invoice"])


@invoice_router.get(
    "/{order_id}",
    description="Get invoice PDF for order\nRequired permissions: order.own:read",
)
async def get_invoice(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    user: HeaderUser = Depends(require_permissions(Permissions.ORDER_OWN_READ)),
):
    order_service = OrderService(db)
    order = await order_service.get(order_id)
    if not order:
        raise NotFoundProblem(detail="Order not found")

    if order.user_uuid != user.uuid:
        raise ForbiddenProblem(detail="Not allowed")

    generator = InvoiceGenerator(order)
    pdf_bytes = generator.generate_invoice_based_on_invoice_type()

    filename = f"invoice_{order.id}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'},
    )

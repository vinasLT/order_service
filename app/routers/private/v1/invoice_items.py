from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Body, Depends
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel, Field
from rfc9457 import NotFoundProblem
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Permissions
from app.core.utils import create_pagination_page
from app.database.crud import InvoiceItemService, OrderService
from app.database.db.session import get_async_db
from app.database.schemas import InvoiceItemCreate, InvoiceItemRead, InvoiceItemUpdate
from app.schemas.invoice_item import InvoiceItemIn

invoice_items_router = APIRouter(prefix="/{order_id}/invoice-item", tags=["Invoice Items"])

InvoiceItemsPage = create_pagination_page(InvoiceItemRead)


class InvoiceItemCreateIn(BaseModel):
    name: str = Field(..., min_length=1, description="Service/line item name")
    amount: int = Field(..., ge=0, description="Line cost in the invoice currency")
    is_extra_fee: bool = Field(default=False, description="Marks the line as an extra fee")


@invoice_items_router.get(
    "",
    response_model=InvoiceItemsPage,
    description=f"Get invoice items for order, required permissions: {Permissions.ORDER_ALL_READ.value}",
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_READ))],
)
async def get_invoice_items(order_id: int, db: AsyncSession = Depends(get_async_db)):
    order_service = OrderService(db)
    await order_service.get_with_not_found_exception(order_id, "Order")

    invoice_item_service = InvoiceItemService(db)
    stmt = await invoice_item_service.get_by_order_id(order_id, get_stmt=True)

    return await paginate(db, stmt)


@invoice_items_router.post(
    "",
    response_model=InvoiceItemRead,
    description=f"Create invoice item, required permissions: {Permissions.ORDER_ALL_WRITE.value}",
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def create_invoice_item(
    order_id: int,
    data: InvoiceItemCreateIn = Body(...),
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    await order_service.get_with_not_found_exception(order_id, "Order")

    invoice_item_service = InvoiceItemService(db)
    payload = InvoiceItemCreate(**data.model_dump(), order_id=order_id)
    return await invoice_item_service.create(payload)


@invoice_items_router.put(
    "/{invoice_item_id}",
    response_model=InvoiceItemRead,
    description=f"Update invoice item, required permissions: {Permissions.ORDER_ALL_WRITE.value}",
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def update_invoice_item(
    order_id: int,
    invoice_item_id: int,
    data: InvoiceItemIn = Body(...),
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    await order_service.get_with_not_found_exception(order_id, "Order")

    invoice_item_service = InvoiceItemService(db)
    existing = await invoice_item_service.get(invoice_item_id)
    if not existing or existing.order_id != order_id:
        raise NotFoundProblem("Invoice item not found")

    update_payload = InvoiceItemUpdate(**data.model_dump(exclude_unset=True), order_id=order_id)
    return await invoice_item_service.update(invoice_item_id, update_payload)


@invoice_items_router.delete(
    "/{invoice_item_id}",
    description=f"Delete invoice item, required permissions: {Permissions.ORDER_ALL_DELETE.value}",
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_DELETE))],
)
async def delete_invoice_item(order_id: int, invoice_item_id: int, db: AsyncSession = Depends(get_async_db)):
    order_service = OrderService(db)
    await order_service.get_with_not_found_exception(order_id, "Order")

    invoice_item_service = InvoiceItemService(db)
    existing = await invoice_item_service.get(invoice_item_id)
    if not existing or existing.order_id != order_id:
        raise NotFoundProblem("Invoice item not found")

    await invoice_item_service.delete(invoice_item_id)
    return {"status": "deleted"}

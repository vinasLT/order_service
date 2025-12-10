from typing import Sequence, Any, Coroutine

from sqlalchemy import select, or_, Select, Row, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService
from app.database.crud.invoice_items import InvoiceItemService
from app.database.models import Order
from app.database.models.order import Order, InvoiceItems
from app.database.schemas import InvoiceItemCreate
from app.database.schemas.order import OrderCreate, OrderUpdate


class OrderService(BaseService[Order, OrderCreate, OrderUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)

    async def exists_by_lot_id(self, lot_id: int) -> bool:
        query = select(Order.id).where(Order.lot_id == lot_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def exists_by_vin(self, vin: str) -> bool:
        query = select(Order.id).where(Order.vin == vin)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def create_invoice_items_batch(
        self,
        order_id: int,
        items: Sequence[InvoiceItemCreate],
    ) -> list[InvoiceItems]:
        if not items:
            return []

        invoice_service = InvoiceItemService(self.session)
        normalized_items = [
            item if item.order_id == order_id else item.model_copy(update={"order_id": order_id})
            for item in items
        ]
        return await invoice_service.create_batch(normalized_items)

    async def get_all_with_search(
        self,
        search: str | None = None,
        get_stmt: bool = True,
        user_uuid: str | None = None,
    ) -> Select[tuple[Order]] | Sequence[Order]:
        stmt = select(Order)

        if user_uuid:
            stmt = stmt.where(Order.user_uuid == user_uuid)

        if search:
            stmt = stmt.where(
                or_(
                    Order.vin.ilike(f"%{search}%"),
                    Order.auction.ilike(f"%{search}%"),
                    Order.lot_id.ilike(f"%{search}%"),
                    Order.vehicle_name.ilike(f"%{search}%"),
                )
            )
        if get_stmt:
            return stmt
        result = await self.session.execute(stmt)
        return result.scalars().all()

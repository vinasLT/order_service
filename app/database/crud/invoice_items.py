from typing import Sequence, Any, Coroutine

from sqlalchemy import select, Select, Row, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService
from app.database.models.order import InvoiceItems
from app.database.schemas import InvoiceItemCreate, InvoiceItemUpdate


class InvoiceItemService(BaseService[InvoiceItems, InvoiceItemCreate, InvoiceItemUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(InvoiceItems, session)

    async def create_batch(self, items: Sequence[InvoiceItemCreate]) -> list[InvoiceItems]:
        if not items:
            return []

        invoice_items = [InvoiceItems(**item.model_dump()) for item in items]
        self.session.add_all(invoice_items)
        await self.session.commit()

        for invoice_item in invoice_items:
            await self.session.refresh(invoice_item)

        return list(invoice_items)

    async def get_by_order_id(
        self, order_id: int, get_stmt: bool = False
    ) -> Select[tuple[InvoiceItems]] | Sequence[InvoiceItems]:
        query = select(InvoiceItems).where(InvoiceItems.order_id == order_id)
        if get_stmt:
            return query
        result = await self.session.execute(query)
        return result.scalars().all()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService
from app.database.models import CustomInvoice
from app.database.schemas import CustomInvoiceCreate, CustomInvoiceUpdate
from app.enums.custom_invoice_status import CustomInvoiceStatus


class CustomInvoiceService(BaseService[CustomInvoice, CustomInvoiceCreate, CustomInvoiceUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(CustomInvoice, session)

    async def get_by_order_id(self, order_id: int) -> CustomInvoice | None:
        statuses_priority = (CustomInvoiceStatus.AVAILABLE, CustomInvoiceStatus.PENDING)
        for status in statuses_priority:
            query = (
                select(CustomInvoice)
                .where(CustomInvoice.order_id == order_id, CustomInvoice.status == status)
                .order_by(CustomInvoice.created_at.desc())
            )
            result = await self.session.execute(query)
            invoice = result.scalars().first()
            if invoice:
                return invoice
        return None

    async def get_by_file_id(self, file_id: int) -> CustomInvoice | None:
        query = select(CustomInvoice).where(CustomInvoice.file_id == file_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService
from app.database.models import AuctionInvoice
from app.database.schemas import AuctionInvoiceCreate, AuctionInvoiceUpdate
from app.enums.custom_invoice_status import FileInvoiceStatus


class AuctionInvoiceService(BaseService[AuctionInvoice, AuctionInvoiceCreate, AuctionInvoiceUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(AuctionInvoice, session)

    async def get_by_order_id(self, order_id: int) -> AuctionInvoice | None:
        statuses_priority = (FileInvoiceStatus.AVAILABLE, FileInvoiceStatus.PENDING)
        for status in statuses_priority:
            query = (
                select(AuctionInvoice)
                .where(AuctionInvoice.order_id == order_id, AuctionInvoice.status == status)
                .order_by(AuctionInvoice.created_at.desc())
            )
            result = await self.session.execute(query)
            invoice = result.scalars().first()
            if invoice:
                return invoice
        return None

    async def get_by_file_id(self, file_id: int) -> AuctionInvoice | None:
        query = select(AuctionInvoice).where(AuctionInvoice.file_id == file_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

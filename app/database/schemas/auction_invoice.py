from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums.custom_invoice_status import FileInvoiceStatus


class AuctionInvoiceBase(BaseModel):
    file_id: int = Field(..., description="File ID for the uploaded invoice")
    order_id: int = Field(..., description="Order ID this invoice belongs to")
    status: FileInvoiceStatus = Field(
        FileInvoiceStatus.PENDING,
        description="Auction invoice status",
    )


class AuctionInvoiceCreate(AuctionInvoiceBase):
    pass


class AuctionInvoiceUpdate(BaseModel):
    file_id: int | None = None
    order_id: int | None = None
    status: FileInvoiceStatus | None = None


class AuctionInvoiceRead(AuctionInvoiceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

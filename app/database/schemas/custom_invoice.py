from pydantic import BaseModel, ConfigDict, Field

from app.enums.custom_invoice_status import CustomInvoiceStatus
from datetime import datetime

class CustomInvoiceBase(BaseModel):
    file_id: int = Field(..., description="File ID for the uploaded invoice")
    order_id: int = Field(..., description="Order ID this invoice belongs to")
    status: CustomInvoiceStatus = Field(CustomInvoiceStatus.PENDING, description="Custom invoice status")


class CustomInvoiceCreate(CustomInvoiceBase):
    pass


class CustomInvoiceUpdate(BaseModel):
    file_id: int | None = None
    order_id: int | None = None
    status: CustomInvoiceStatus | None = None


class CustomInvoiceRead(CustomInvoiceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

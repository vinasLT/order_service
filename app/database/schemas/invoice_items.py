from pydantic import BaseModel, ConfigDict, Field


class InvoiceItemBase(BaseModel):
    name: str = Field(..., min_length=1, description="Service/line item name")
    amount: int = Field(..., ge=0, description="Line cost in the invoice currency")
    is_extra_fee: bool = Field(default=False, description="Marks the line as an extra fee")
    order_id: int = Field(..., description="Order ID the item belongs to")


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItemUpdate(BaseModel):
    name: str | None = None
    amount: int | None = None
    is_extra_fee: bool | None = None
    order_id: int | None = None


class InvoiceItemRead(InvoiceItemBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

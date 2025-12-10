from pydantic import BaseModel


class InvoiceItemIn(BaseModel):
    name: str | None = None
    amount: int | None = None
    is_extra_fee: bool | None = None
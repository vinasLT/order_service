from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums.order import OrderStatusEnum


class OrderStatusHistoryBase(BaseModel):
    order_id: int = Field(..., description="Order ID")
    status: OrderStatusEnum = Field(..., description="Delivery status")


class OrderStatusHistoryCreate(OrderStatusHistoryBase):
    pass


class OrderStatusHistoryUpdate(BaseModel):
    order_id: int | None = None
    status: OrderStatusEnum | None = None


class OrderStatusHistoryRead(OrderStatusHistoryBase):
    id: int
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)

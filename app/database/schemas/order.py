from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.enums.auction import AuctionEnum
from app.enums.order import InvoiceTypeEnum, OrderStatusEnum


class OrderBase(BaseModel):
    auction: AuctionEnum | None = Field(..., description="Source auction")
    order_date: datetime | None = Field(
        ...,
        description="Order creation date (if not provided, DB sets the current time)",
    )
    lot_id: int = Field(..., description="Lot identifier")
    vehicle_value: int = Field(..., ge=0, description="Vehicle price")
    invoice_type: InvoiceTypeEnum = Field(
        default=InvoiceTypeEnum.DEFAULT,
        description="Invoice type",
    )
    vehicle_type: str = Field(default="CAR", description="Vehicle type")
    vin: str = Field(..., min_length=1, description="Vehicle VIN")
    vehicle_name: str = Field(..., min_length=1, description="Vehicle model/name")
    keys: bool = Field(default=False, description="Keys present")
    damage: bool = Field(default=False, description="Vehicle damaged")
    color: str = Field(default="Unknown", description="Vehicle color")
    auto_generated: bool = Field(default=False, description="Order created automatically")
    fee_type: str = Field(..., description="Name of the fee type")

    location_id: int = Field(..., description="Location ID")

    destination_id: int | None = Field(None, description="Destination ID")

    terminal_id: int = Field(..., description="Terminal ID")
    fee_type_id: int = Field(..., description="Fee type ID")
    user_uuid: str = Field(..., description="UUID of the user who own the order")


class OrderCreate(OrderBase):
    location_name: str
    location_city: str | None
    location_state: str | None
    location_postal_code: str | None
    destination_name: str | None
    terminal_name: str
    fee_type_name: str


class OrderUpdate(BaseModel):
    auction: AuctionEnum | None = None
    order_date: datetime | None = None
    lot_id: int | None = None
    vehicle_value: int | None = None
    invoice_type: InvoiceTypeEnum | None = None
    vehicle_type: str | None = None
    vin: str | None = None
    vehicle_name: str | None = None
    keys: bool | None = None
    damage: bool | None = None
    color: str | None = None
    auto_generated: bool | None = None
    fee_type: str | None = None
    delivery_status: OrderStatusEnum | None = None

    tracking_link: str | None = None

    location_id: int | None = None
    location_name: str | None = None
    location_city: str | None = None
    location_state: str | None = None
    location_postal_code: str | None = None

    destination_id: int | None = None
    destination_name: str | None = None

    terminal_id: int | None = None
    terminal_name: str | None = None
    fee_type_id: int | None = None
    fee_type_name: str | None = None
    user_uuid: str | None = None


class OrderRead(OrderBase):
    id: int
    created_at: datetime
    updated_at: datetime
    delivery_status: OrderStatusEnum
    location_name: str
    location_city: str | None
    location_state: str | None
    location_postal_code: str | None
    destination_name: str
    terminal_name: str
    fee_type_name: str
    tracking_link: str | None = None

    model_config = ConfigDict(from_attributes=True)

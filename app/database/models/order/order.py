from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.auction import AuctionEnum
from app.enums.order import InvoiceTypeEnum, OrderStatusEnum
from ..base import Base
from ..mixins import IdMixin, TimestampMixin


if TYPE_CHECKING:
    from app.database.models import InvoiceItems, OrderStatusHistory


class Order(IdMixin, TimestampMixin, Base):
    __tablename__ = "order"

    # -- order fields --
    auction: Mapped[AuctionEnum] = mapped_column(Enum(AuctionEnum), nullable=True)
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda : datetime.now(timezone.utc)
    )
    lot_id: Mapped[int] = mapped_column(nullable=False, unique=True)
    vehicle_value: Mapped[int] = mapped_column(nullable=False)

    vehicle_type: Mapped[str] = mapped_column(nullable=False, default="CAR")
    vin: Mapped[str] = mapped_column(unique=True, nullable=False)
    vehicle_name: Mapped[str] = mapped_column(nullable=False)
    keys: Mapped[bool] = mapped_column(nullable=False, default=False)
    damage: Mapped[bool] = mapped_column(nullable=False, default=False)
    color: Mapped[str] = mapped_column(nullable=False, default="Unknown")

    auto_generated: Mapped[bool] = mapped_column(nullable=False, default=False)
    fee_type: Mapped[str] = mapped_column(nullable=False)
    delivery_status: Mapped[OrderStatusEnum] = mapped_column(
        Enum(OrderStatusEnum), nullable=False, default=OrderStatusEnum.PENDING_PAYMENT
    )

    # --- external calculator fields ---
    # -- location
    location_id: Mapped[int] = mapped_column(nullable=False)
    location_name: Mapped[str] = mapped_column(nullable=False)
    location_city: Mapped[str] = mapped_column(nullable=True)
    location_state: Mapped[str] = mapped_column(nullable=True)
    location_postal_code: Mapped[str] = mapped_column(nullable=True)

    # -- terminal
    terminal_id: Mapped[int] = mapped_column(nullable=False)
    terminal_name: Mapped[str] = mapped_column(nullable=False)
    # -- fee_type
    fee_type_id: Mapped[int] = mapped_column(nullable=False)
    fee_type_name: Mapped[str] = mapped_column(nullable=False)

    user_uuid: Mapped[str] = mapped_column(nullable=False)

    # -- relationships --
    invoice_items: Mapped[list["InvoiceItems"]] = relationship(
        "InvoiceItems", back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        "OrderStatusHistory", back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

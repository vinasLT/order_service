from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.order import OrderStatusEnum
from ..base import Base
from ..mixins import IdMixin

if TYPE_CHECKING:
    from app.database.models import Order


class OrderStatusHistory(IdMixin, Base):
    __tablename__ = "order_status_history"

    order_id: Mapped[int] = mapped_column(ForeignKey("order.id"), nullable=False)
    status: Mapped[OrderStatusEnum] = mapped_column(Enum(OrderStatusEnum), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="status_history")

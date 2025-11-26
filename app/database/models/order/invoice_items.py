from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column

from ..base import Base

if TYPE_CHECKING:
    from app.database.models import Order


class InvoiceItems(Base):
    __tablename__ = "invoice_item"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(nullable=False)
    amount: Mapped[int] = mapped_column(nullable=False)
    is_extra_fee: Mapped[bool] = mapped_column(nullable=False)

    order_id: Mapped[int] = mapped_column(ForeignKey('order.id'), nullable=False)

    order: Mapped["Order"] = relationship('Order', back_populates='invoice_items', lazy='selectin')

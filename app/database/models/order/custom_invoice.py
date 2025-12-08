from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import Base, TimestampMixin, IdMixin
from app.enums.custom_invoice_status import CustomInvoiceStatus

if TYPE_CHECKING:
    from app.database.models import Order


class CustomInvoice(IdMixin, TimestampMixin, Base):
    __tablename__ = "custom_invoice"

    file_id: Mapped[int] = mapped_column(nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("order.id"), nullable=False, unique=True)
    status: Mapped[CustomInvoiceStatus] = mapped_column(Enum(CustomInvoiceStatus),
                                                        nullable=False, default=CustomInvoiceStatus.PENDING)

    order: Mapped["Order"] = relationship("Order", back_populates="custom_invoice", lazy="selectin")

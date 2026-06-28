from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import Base, TimestampMixin, IdMixin
from app.database.types import file_invoice_status_enum
from app.enums.custom_invoice_status import FileInvoiceStatus

if TYPE_CHECKING:
    from app.database.models import Order


class CustomInvoice(IdMixin, TimestampMixin, Base):
    __tablename__ = "custom_invoice"

    file_id: Mapped[int] = mapped_column(nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("order.id"), nullable=False, unique=True)
    status: Mapped[FileInvoiceStatus] = mapped_column(
        file_invoice_status_enum,
        nullable=False,
        default=FileInvoiceStatus.PENDING,
    )

    order: Mapped["Order"] = relationship("Order", back_populates="custom_invoice", lazy="selectin")

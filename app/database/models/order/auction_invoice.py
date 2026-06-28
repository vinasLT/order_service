from typing import TYPE_CHECKING

from app.database.models import Base, IdMixin, TimestampMixin
from app.database.types import file_invoice_status_enum
from app.enums.custom_invoice_status import FileInvoiceStatus
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.database.models import Order

class AuctionInvoice(IdMixin, TimestampMixin, Base):
    __tablename__ = "auction_invoice"

    order_id: Mapped[int] = mapped_column(ForeignKey("order.id"), nullable=False, unique=True)

    file_id: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[FileInvoiceStatus] = mapped_column(
        file_invoice_status_enum,
        nullable=False,
        default=FileInvoiceStatus.PENDING,
    )

    order: Mapped["Order"] = relationship("Order", back_populates="auction_invoice", lazy="selectin")

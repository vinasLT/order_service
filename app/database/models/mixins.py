from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column


def _utcnow() -> datetime:
    """Return aware UTC datetime for default/onupdate callables."""
    return datetime.now(timezone.utc)


class IdMixin:
    id: Mapped[int] = mapped_column(primary_key=True, index=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

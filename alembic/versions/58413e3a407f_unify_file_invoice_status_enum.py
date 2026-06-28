"""unify file invoice status enum

Revision ID: 58413e3a407f
Revises: 4bf673450a31
Create Date: 2026-06-28 16:04:08.429745

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58413e3a407f'
down_revision: Union[str, Sequence[str], None] = '4bf673450a31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return

    op.execute(
        "ALTER TABLE auction_invoice "
        "ALTER COLUMN status TYPE custominvoicestatus "
        "USING status::text::custominvoicestatus"
    )
    op.execute('DROP TYPE fileinvoicestatus')


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return

    file_invoice_status = sa.Enum('PENDING', 'AVAILABLE', name='fileinvoicestatus')
    file_invoice_status.create(bind, checkfirst=True)

    op.execute(
        "ALTER TABLE auction_invoice "
        "ALTER COLUMN status TYPE fileinvoicestatus "
        "USING status::text::fileinvoicestatus"
    )

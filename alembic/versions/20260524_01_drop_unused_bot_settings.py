"""drop unused bot settings columns

Revision ID: 20260524_01
Revises: 20260520_02
Create Date: 2026-05-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260524_01"
down_revision: Union[str, None] = "20260520_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("vendor_bot_settings", "allow_product_qa")
    op.drop_column("vendor_bot_settings", "allow_office_qa")


def downgrade() -> None:
    op.add_column(
        "vendor_bot_settings",
        sa.Column("allow_product_qa", sa.Boolean(), server_default=sa.text("1"), nullable=False),
    )
    op.add_column(
        "vendor_bot_settings",
        sa.Column("allow_office_qa", sa.Boolean(), server_default=sa.text("1"), nullable=False),
    )

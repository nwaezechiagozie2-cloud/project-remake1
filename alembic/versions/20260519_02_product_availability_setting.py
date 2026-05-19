"""add product availability bot setting

Revision ID: 20260519_02
Revises: 20260519_01
Create Date: 2026-05-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_02"
down_revision: Union[str, None] = "20260519_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    inspector = _inspector()
    if _table_exists(inspector, "vendor_bot_settings") and not _column_exists(
        inspector,
        "vendor_bot_settings",
        "use_product_availability",
    ):
        op.add_column(
            "vendor_bot_settings",
            sa.Column("use_product_availability", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        )


def downgrade() -> None:
    inspector = _inspector()
    if _table_exists(inspector, "vendor_bot_settings") and _column_exists(
        inspector,
        "vendor_bot_settings",
        "use_product_availability",
    ):
        op.drop_column("vendor_bot_settings", "use_product_availability")

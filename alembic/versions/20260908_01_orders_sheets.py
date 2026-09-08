"""Add orders table and Google Sheets sync support

Revision ID: 20260908_01
Revises: 20260605_01
Create Date: 2026-09-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260908_01"
down_revision: Union[str, None] = "20260605_01"
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

    if not _table_exists(inspector, "orders"):
        op.create_table(
            "orders",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("vendor_id", sa.Integer(), nullable=False),
            sa.Column("customer_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=80), nullable=False, server_default=sa.text("'ACCOUNT_DETAILS_SENT'")),
            sa.Column("order_ref", sa.String(length=40), nullable=False),
            sa.Column("customer_name", sa.String(length=255), nullable=True),
            sa.Column("customer_phone", sa.String(length=50), nullable=True),
            sa.Column("customer_platform", sa.String(length=20), nullable=False),
            sa.Column("customer_handle", sa.String(length=100), nullable=True),
            sa.Column("order_details", sa.Text(), nullable=True),
            sa.Column("sheets_synced", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("sheets_sync_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("sheets_synced_at", sa.DateTime(), nullable=True),
            sa.Column("sheets_last_error", sa.Text(), nullable=True),
            sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
            sa.Column("sync_claimed_until", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("order_ref"),
            sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_orders_vendor_id", "orders", ["vendor_id"])
        op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
        op.create_index("ix_orders_sheets_synced", "orders", ["sheets_synced"])
        op.create_index("ix_orders_next_attempt_at", "orders", ["next_attempt_at"])

    if not _table_exists(inspector, "vendor_google_sheets_tokens"):
        op.create_table(
            "vendor_google_sheets_tokens",
            sa.Column("vendor_id", sa.Integer(), nullable=False),
            sa.Column("token_json", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("vendor_id"),
            sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        )

    if _table_exists(inspector, "vendor_bot_settings"):
        if not _column_exists(inspector, "vendor_bot_settings", "sheets_sync_enabled"):
            op.add_column("vendor_bot_settings", sa.Column("sheets_sync_enabled", sa.Boolean(), server_default=sa.text("0"), nullable=False))
        if not _column_exists(inspector, "vendor_bot_settings", "sheets_spreadsheet_id"):
            op.add_column("vendor_bot_settings", sa.Column("sheets_spreadsheet_id", sa.String(length=100), nullable=True))
        if not _column_exists(inspector, "vendor_bot_settings", "sheets_spreadsheet_title"):
            op.add_column("vendor_bot_settings", sa.Column("sheets_spreadsheet_title", sa.String(length=255), nullable=True))
        if not _column_exists(inspector, "vendor_bot_settings", "sheets_tab_name"):
            op.add_column("vendor_bot_settings", sa.Column("sheets_tab_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    inspector = _inspector()

    if _table_exists(inspector, "vendor_bot_settings"):
        if _column_exists(inspector, "vendor_bot_settings", "sheets_tab_name"):
            op.drop_column("vendor_bot_settings", "sheets_tab_name")
        if _column_exists(inspector, "vendor_bot_settings", "sheets_spreadsheet_title"):
            op.drop_column("vendor_bot_settings", "sheets_spreadsheet_title")
        if _column_exists(inspector, "vendor_bot_settings", "sheets_spreadsheet_id"):
            op.drop_column("vendor_bot_settings", "sheets_spreadsheet_id")
        if _column_exists(inspector, "vendor_bot_settings", "sheets_sync_enabled"):
            op.drop_column("vendor_bot_settings", "sheets_sync_enabled")

    if _table_exists(inspector, "vendor_google_sheets_tokens"):
        op.drop_table("vendor_google_sheets_tokens")

    if _table_exists(inspector, "orders"):
        op.drop_index("ix_orders_next_attempt_at", table_name="orders")
        op.drop_index("ix_orders_sheets_synced", table_name="orders")
        op.drop_index("ix_orders_customer_id", table_name="orders")
        op.drop_index("ix_orders_vendor_id", table_name="orders")
        op.drop_table("orders")

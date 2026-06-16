"""Add Telegram support

Revision ID: 20260605_01
Revises: 20260524_01
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_01"
down_revision: Union[str, None] = "20260524_01"
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


def _unique_constraint_exists(inspector: sa.Inspector, table_name: str, column_names: list[str]) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    target = tuple(column_names)
    for constraint in inspector.get_unique_constraints(table_name):
        if tuple(constraint.get("column_names") or []) == target:
            return True
    return False


def upgrade() -> None:
    inspector = _inspector()

    if _table_exists(inspector, "vendors"):
        if not _column_exists(inspector, "vendors", "telegram_bot_token"):
            op.add_column("vendors", sa.Column("telegram_bot_token", sa.Text(), nullable=True))
        if not _column_exists(inspector, "vendors", "telegram_vendor_chat_id"):
            op.add_column("vendors", sa.Column("telegram_vendor_chat_id", sa.String(length=100), nullable=True))
        if not _unique_constraint_exists(inspector, "vendors", ["telegram_vendor_chat_id"]):
            op.create_unique_constraint("uq_vendors_telegram_vendor_chat_id", "vendors", ["telegram_vendor_chat_id"])

    if _table_exists(inspector, "customers"):
        if not _column_exists(inspector, "customers", "telegram_id"):
            op.add_column("customers", sa.Column("telegram_id", sa.String(length=100), nullable=True))
        if not _column_exists(inspector, "customers", "telegram_chat_id"):
            op.add_column("customers", sa.Column("telegram_chat_id", sa.String(length=100), nullable=True))
        if not _unique_constraint_exists(inspector, "customers", ["telegram_id"]):
            op.create_unique_constraint("uq_customers_telegram_id", "customers", ["telegram_id"])
        if not _unique_constraint_exists(inspector, "customers", ["telegram_chat_id"]):
            op.create_unique_constraint("uq_customers_telegram_chat_id", "customers", ["telegram_chat_id"])


def downgrade() -> None:
    inspector = _inspector()

    if _table_exists(inspector, "customers"):
        if _unique_constraint_exists(inspector, "customers", ["telegram_chat_id"]):
            op.drop_constraint("uq_customers_telegram_chat_id", "customers", type_="unique")
        if _unique_constraint_exists(inspector, "customers", ["telegram_id"]):
            op.drop_constraint("uq_customers_telegram_id", "customers", type_="unique")
        if _column_exists(inspector, "customers", "telegram_chat_id"):
            op.drop_column("customers", "telegram_chat_id")
        if _column_exists(inspector, "customers", "telegram_id"):
            op.drop_column("customers", "telegram_id")

    if _table_exists(inspector, "vendors"):
        if _unique_constraint_exists(inspector, "vendors", ["telegram_vendor_chat_id"]):
            op.drop_constraint("uq_vendors_telegram_vendor_chat_id", "vendors", type_="unique")
        if _column_exists(inspector, "vendors", "telegram_vendor_chat_id"):
            op.drop_column("vendors", "telegram_vendor_chat_id")
        if _column_exists(inspector, "vendors", "telegram_bot_token"):
            op.drop_column("vendors", "telegram_bot_token")

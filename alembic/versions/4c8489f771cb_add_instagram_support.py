"""Add Instagram support

Revision ID: 4c8489f771cb
Revises: 20260420_02
Create Date: 2026-05-06 19:16:20.062461

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '4c8489f771cb'
down_revision: Union[str, None] = '20260420_02'
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


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    inspector = _inspector()

    if not _table_exists(inspector, "vendor_business_info"):
        op.create_table(
            "vendor_business_info",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("vendor_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("source_type", sa.String(length=50), server_default=sa.text("'TEXT'"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_vendor_business_info_vendor_id"),
            "vendor_business_info",
            ["vendor_id"],
            unique=False,
        )
    elif not _index_exists(inspector, "vendor_business_info", op.f("ix_vendor_business_info_vendor_id")):
        op.create_index(
            op.f("ix_vendor_business_info_vendor_id"),
            "vendor_business_info",
            ["vendor_id"],
            unique=False,
        )

    if _table_exists(inspector, "conversation_states"):
        op.alter_column(
            "conversation_states",
            "updated_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("now()"),
            existing_nullable=False,
        )

    if _table_exists(inspector, "customers"):
        if not _column_exists(inspector, "customers", "instagram_id"):
            op.add_column("customers", sa.Column("instagram_id", sa.String(length=100), nullable=True))
        op.alter_column(
            "customers",
            "whatsapp_number",
            existing_type=mysql.VARCHAR(length=50),
            nullable=True,
        )
        if not _unique_constraint_exists(inspector, "customers", ["instagram_id"]):
            op.create_unique_constraint("uq_customers_instagram_id", "customers", ["instagram_id"])

    if _table_exists(inspector, "messages"):
        op.alter_column(
            "messages",
            "created_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("now()"),
            existing_nullable=False,
        )

    if _table_exists(inspector, "order_lifecycle_states"):
        op.alter_column(
            "order_lifecycle_states",
            "updated_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("now()"),
            existing_nullable=False,
        )

    if _table_exists(inspector, "products"):
        op.alter_column(
            "products",
            "created_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("now()"),
            existing_nullable=False,
        )

    if _table_exists(inspector, "vendor_bot_settings"):
        op.alter_column(
            "vendor_bot_settings",
            "updated_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("now()"),
            existing_nullable=False,
        )

    if _table_exists(inspector, "vendor_customers"):
        op.alter_column(
            "vendor_customers",
            "first_seen_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("now()"),
            existing_nullable=False,
        )
        op.alter_column(
            "vendor_customers",
            "last_seen_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("now()"),
            existing_nullable=False,
        )

    if _table_exists(inspector, "vendor_google_tokens"):
        op.alter_column(
            "vendor_google_tokens",
            "updated_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("now()"),
            existing_nullable=False,
        )

    if _table_exists(inspector, "vendors"):
        if not _column_exists(inspector, "vendors", "instagram_page_id"):
            op.add_column("vendors", sa.Column("instagram_page_id", sa.String(length=100), nullable=True))
        if not _column_exists(inspector, "vendors", "instagram_page_token"):
            op.add_column("vendors", sa.Column("instagram_page_token", sa.Text(), nullable=True))
        op.alter_column(
            "vendors",
            "created_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("now()"),
            existing_nullable=False,
        )
        if not _unique_constraint_exists(inspector, "vendors", ["instagram_page_id"]):
            op.create_unique_constraint("uq_vendors_instagram_page_id", "vendors", ["instagram_page_id"])


def downgrade() -> None:
    inspector = _inspector()

    if _table_exists(inspector, "vendors"):
        if _unique_constraint_exists(inspector, "vendors", ["instagram_page_id"]):
            op.drop_constraint("uq_vendors_instagram_page_id", "vendors", type_="unique")
        if _column_exists(inspector, "vendors", "instagram_page_token"):
            op.drop_column("vendors", "instagram_page_token")
        if _column_exists(inspector, "vendors", "instagram_page_id"):
            op.drop_column("vendors", "instagram_page_id")

    if _table_exists(inspector, "vendor_google_tokens"):
        op.alter_column(
            "vendor_google_tokens",
            "updated_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("(now())"),
            existing_nullable=False,
        )

    if _table_exists(inspector, "vendor_customers"):
        op.alter_column(
            "vendor_customers",
            "last_seen_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("(now())"),
            existing_nullable=False,
        )
        op.alter_column(
            "vendor_customers",
            "first_seen_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("(now())"),
            existing_nullable=False,
        )

    if _table_exists(inspector, "vendor_bot_settings"):
        op.alter_column(
            "vendor_bot_settings",
            "updated_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("(now())"),
            existing_nullable=False,
        )

    if _table_exists(inspector, "products"):
        op.alter_column(
            "products",
            "created_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("(now())"),
            existing_nullable=False,
        )

    if _table_exists(inspector, "order_lifecycle_states"):
        op.alter_column(
            "order_lifecycle_states",
            "updated_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("(now())"),
            existing_nullable=False,
        )

    if _table_exists(inspector, "messages"):
        op.alter_column(
            "messages",
            "created_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("(now())"),
            existing_nullable=False,
        )

    if _table_exists(inspector, "customers"):
        if _unique_constraint_exists(inspector, "customers", ["instagram_id"]):
            op.drop_constraint("uq_customers_instagram_id", "customers", type_="unique")
        if _column_exists(inspector, "customers", "instagram_id"):
            op.drop_column("customers", "instagram_id")
        op.alter_column(
            "customers",
            "whatsapp_number",
            existing_type=mysql.VARCHAR(length=50),
            nullable=False,
        )

    if _table_exists(inspector, "conversation_states"):
        op.alter_column(
            "conversation_states",
            "updated_at",
            existing_type=mysql.DATETIME(),
            server_default=sa.text("(now())"),
            existing_nullable=False,
        )

    if _table_exists(inspector, "vendor_business_info"):
        if _index_exists(inspector, "vendor_business_info", op.f("ix_vendor_business_info_vendor_id")):
            op.drop_index(op.f("ix_vendor_business_info_vendor_id"), table_name="vendor_business_info")
        op.drop_table("vendor_business_info")

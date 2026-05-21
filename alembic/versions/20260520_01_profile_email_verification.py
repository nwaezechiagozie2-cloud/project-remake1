"""add profile email verification

Revision ID: 20260520_01
Revises: 20260519_02
Create Date: 2026-05-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260520_01"
down_revision: Union[str, None] = "20260519_02"
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


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    inspector = _inspector()

    if _table_exists(inspector, "vendors"):
        if not _column_exists(inspector, "vendors", "email_verified_at"):
            op.add_column("vendors", sa.Column("email_verified_at", sa.DateTime(), nullable=True))
        if not _column_exists(inspector, "vendors", "pending_email"):
            op.add_column("vendors", sa.Column("pending_email", sa.String(length=255), nullable=True))
            op.create_unique_constraint("uq_vendors_pending_email", "vendors", ["pending_email"])

    if not _table_exists(inspector, "email_verification_tokens"):
        op.create_table(
            "email_verification_tokens",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("vendor_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("purpose", sa.String(length=40), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash", name="uq_email_verification_tokens_token_hash"),
        )
        op.create_index("ix_email_verification_tokens_vendor_id", "email_verification_tokens", ["vendor_id"])


def downgrade() -> None:
    inspector = _inspector()

    if _table_exists(inspector, "email_verification_tokens"):
        if _index_exists(inspector, "email_verification_tokens", "ix_email_verification_tokens_vendor_id"):
            op.drop_index("ix_email_verification_tokens_vendor_id", table_name="email_verification_tokens")
        op.drop_table("email_verification_tokens")

    if _table_exists(inspector, "vendors"):
        if _column_exists(inspector, "vendors", "pending_email"):
            op.drop_constraint("uq_vendors_pending_email", "vendors", type_="unique")
            op.drop_column("vendors", "pending_email")
        if _column_exists(inspector, "vendors", "email_verified_at"):
            op.drop_column("vendors", "email_verified_at")

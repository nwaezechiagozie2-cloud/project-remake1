"""add oauth login provider ids

Revision ID: 20260520_02
Revises: 20260520_01
Create Date: 2026-05-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260520_02"
down_revision: Union[str, None] = "20260520_01"
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
    if not _table_exists(inspector, "vendors"):
        return

    if not _column_exists(inspector, "vendors", "google_subject_id"):
        op.add_column("vendors", sa.Column("google_subject_id", sa.String(length=255), nullable=True))
        op.create_unique_constraint("uq_vendors_google_subject_id", "vendors", ["google_subject_id"])

    if not _column_exists(inspector, "vendors", "instagram_user_id"):
        op.add_column("vendors", sa.Column("instagram_user_id", sa.String(length=255), nullable=True))
        op.create_unique_constraint("uq_vendors_instagram_user_id", "vendors", ["instagram_user_id"])


def downgrade() -> None:
    inspector = _inspector()
    if not _table_exists(inspector, "vendors"):
        return

    if _column_exists(inspector, "vendors", "instagram_user_id"):
        op.drop_constraint("uq_vendors_instagram_user_id", "vendors", type_="unique")
        op.drop_column("vendors", "instagram_user_id")

    if _column_exists(inspector, "vendors", "google_subject_id"):
        op.drop_constraint("uq_vendors_google_subject_id", "vendors", type_="unique")
        op.drop_column("vendors", "google_subject_id")

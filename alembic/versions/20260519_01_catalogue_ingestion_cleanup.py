"""catalogue ingestion and remove vendor knowledge entries

Revision ID: 20260519_01
Revises: 20260518_01
Create Date: 2026-05-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_01"
down_revision: Union[str, None] = "20260518_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    inspector = _inspector()

    if not _table_exists(inspector, "vendor_catalogue_uploads"):
        op.create_table(
            "vendor_catalogue_uploads",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("vendor_id", sa.Integer(), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("mime_type", sa.String(length=120), nullable=True),
            sa.Column("source_url", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), server_default=sa.text("'PENDING'"), nullable=False),
            sa.Column("extracted_text", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("processed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_vendor_catalogue_uploads_vendor_id", "vendor_catalogue_uploads", ["vendor_id"])

    if not _table_exists(inspector, "catalogue_import_items"):
        op.create_table(
            "catalogue_import_items",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("upload_id", sa.Integer(), nullable=False),
            sa.Column("vendor_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("price", sa.Numeric(12, 2), nullable=True),
            sa.Column("currency", sa.String(length=10), server_default=sa.text("'NGN'"), nullable=False),
            sa.Column("in_stock", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            sa.Column("raw_text", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), server_default=sa.text("'DRAFT'"), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["upload_id"], ["vendor_catalogue_uploads.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_catalogue_import_items_upload_id", "catalogue_import_items", ["upload_id"])
        op.create_index("ix_catalogue_import_items_vendor_id", "catalogue_import_items", ["vendor_id"])

    if _table_exists(inspector, "vendor_knowledge_entries") and _table_exists(inspector, "vendor_business_info"):
        op.execute(
            """
            INSERT INTO vendor_business_info (vendor_id, title, content, source_type)
            SELECT
                vendor_id,
                COALESCE(NULLIF(title, ''), NULLIF(question, ''), 'Imported knowledge entry') AS title,
                answer AS content,
                'MIGRATED_KNOWLEDGE' AS source_type
            FROM vendor_knowledge_entries
            WHERE answer IS NOT NULL AND answer <> ''
            """
        )

    if _table_exists(inspector, "vendor_knowledge_entries"):
        if _index_exists(inspector, "vendor_knowledge_entries", "ix_vendor_knowledge_entries_vendor_id"):
            op.drop_index("ix_vendor_knowledge_entries_vendor_id", table_name="vendor_knowledge_entries")
        op.drop_table("vendor_knowledge_entries")


def downgrade() -> None:
    inspector = _inspector()

    if not _table_exists(inspector, "vendor_knowledge_entries"):
        op.create_table(
            "vendor_knowledge_entries",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("vendor_id", sa.Integer(), nullable=False),
            sa.Column(
                "entry_type",
                sa.Enum("PRODUCT", "OFFICE", "FAQ", name="vendor_knowledge_entry_type", native_enum=False),
                server_default="FAQ",
                nullable=False,
            ),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("question", sa.Text(), nullable=True),
            sa.Column("answer", sa.Text(), nullable=False),
            sa.Column("keywords", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_vendor_knowledge_entries_vendor_id", "vendor_knowledge_entries", ["vendor_id"])

    if _table_exists(inspector, "catalogue_import_items"):
        if _index_exists(inspector, "catalogue_import_items", "ix_catalogue_import_items_vendor_id"):
            op.drop_index("ix_catalogue_import_items_vendor_id", table_name="catalogue_import_items")
        if _index_exists(inspector, "catalogue_import_items", "ix_catalogue_import_items_upload_id"):
            op.drop_index("ix_catalogue_import_items_upload_id", table_name="catalogue_import_items")
        op.drop_table("catalogue_import_items")

    if _table_exists(inspector, "vendor_catalogue_uploads"):
        if _index_exists(inspector, "vendor_catalogue_uploads", "ix_vendor_catalogue_uploads_vendor_id"):
            op.drop_index("ix_vendor_catalogue_uploads_vendor_id", table_name="vendor_catalogue_uploads")
        op.drop_table("vendor_catalogue_uploads")

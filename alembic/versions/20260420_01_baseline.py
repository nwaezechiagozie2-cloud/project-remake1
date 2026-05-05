"""baseline schema

Revision ID: 20260420_01
Revises: 
Create Date: 2026-04-20 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260420_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


vendor_knowledge_entry_type = sa.Enum(
    "PRODUCT",
    "OFFICE",
    "FAQ",
    name="vendor_knowledge_entry_type",
    native_enum=False,
)
message_direction = sa.Enum(
    "INBOUND",
    "OUTBOUND",
    name="message_direction",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("whatsapp_number", sa.String(length=50), nullable=True),
        sa.Column("whatsapp_token", sa.Text(), nullable=True),
        sa.Column("whatsapp_phone_number_id", sa.String(length=100), nullable=True),
        sa.Column("account_number", sa.String(length=30), nullable=True),
        sa.Column("bank_name", sa.String(length=100), nullable=True),
        sa.Column("account_name", sa.String(length=255), nullable=True),
        sa.Column("product_catalogue_url", sa.Text(), nullable=True),
        sa.Column("product_catalogue_media_id", sa.String(length=255), nullable=True),
        sa.Column("product_catalogue_caption", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_vendors_email"),
        sa.UniqueConstraint("whatsapp_number", name="uq_vendors_whatsapp_number"),
        sa.UniqueConstraint("whatsapp_phone_number_id", name="uq_vendors_whatsapp_phone_number_id"),
    )

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("whatsapp_number", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("delivery_address", sa.Text(), nullable=True),
        sa.UniqueConstraint("whatsapp_number", name="uq_customers_whatsapp_number"),
    )

    op.create_table(
        "vendor_bot_settings",
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("confirm_before_sending_account_details", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("enable_knowledge_base_answers", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("allow_product_qa", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("allow_office_qa", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("vendor_id"),
    )

    op.create_table(
        "vendor_knowledge_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("entry_type", vendor_knowledge_entry_type, nullable=False, server_default="FAQ"),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_vendor_knowledge_entries_vendor_id", "vendor_knowledge_entries", ["vendor_id"])

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("extra_details", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="NGN"),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("video_url", sa.Text(), nullable=True),
        sa.Column("in_stock", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_products_vendor_id", "products", ["vendor_id"])

    op.create_table(
        "vendor_customers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("vendor_id", "customer_id", name="uq_vendor_customer"),
    )

    op.create_table(
        "conversation_states",
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("last_message", sa.Text(), nullable=True),
        sa.Column("google_contact_saved", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("vendor_id", "customer_id"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("direction", message_direction, nullable=False),
        sa.Column("message_type", sa.String(length=30), nullable=False),
        sa.Column("whatsapp_message_id", sa.String(length=255), nullable=True),
        sa.Column("sender_number", sa.String(length=50), nullable=True),
        sa.Column("recipient_number", sa.String(length=50), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "order_lifecycle_states",
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("last_event_text", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("vendor_id", "customer_id"),
    )


def downgrade() -> None:
    op.drop_table("order_lifecycle_states")
    op.drop_table("messages")
    op.drop_table("conversation_states")
    op.drop_table("vendor_customers")
    op.drop_index("ix_products_vendor_id", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_vendor_knowledge_entries_vendor_id", table_name="vendor_knowledge_entries")
    op.drop_table("vendor_knowledge_entries")
    op.drop_table("vendor_bot_settings")
    op.drop_table("customers")
    op.drop_table("vendors")

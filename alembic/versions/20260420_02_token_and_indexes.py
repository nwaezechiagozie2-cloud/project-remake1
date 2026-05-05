"""add vendor google tokens and performance indexes

Revision ID: 20260420_02
Revises: 20260420_01
Create Date: 2026-04-20 10:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260420_02"
down_revision: Union[str, None] = "20260420_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vendor_google_tokens",
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("token_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("vendor_id"),
    )

    op.create_index(
        "ix_messages_vendor_customer_created_at",
        "messages",
        ["vendor_id", "customer_id", "created_at"],
    )
    op.create_index("ix_messages_vendor_created_at", "messages", ["vendor_id", "created_at"])
    op.create_index("ix_conversation_states_vendor_updated_at", "conversation_states", ["vendor_id", "updated_at"])
    op.create_index("ix_conversation_states_customer_id", "conversation_states", ["customer_id"])
    op.create_index("ix_vendor_customers_vendor_last_seen", "vendor_customers", ["vendor_id", "last_seen_at"])
    op.create_index("ix_vendor_customers_customer_id", "vendor_customers", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_vendor_customers_customer_id", table_name="vendor_customers")
    op.drop_index("ix_vendor_customers_vendor_last_seen", table_name="vendor_customers")
    op.drop_index("ix_conversation_states_customer_id", table_name="conversation_states")
    op.drop_index("ix_conversation_states_vendor_updated_at", table_name="conversation_states")
    op.drop_index("ix_messages_vendor_created_at", table_name="messages")
    op.drop_index("ix_messages_vendor_customer_created_at", table_name="messages")

    op.drop_table("vendor_google_tokens")

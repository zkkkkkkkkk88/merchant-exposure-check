"""Add confirmed merchant profile facts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_visibility_profiles"
down_revision: str | None = "0004_analysis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "merchant_profile_facts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("merchant_id", sa.Uuid(), nullable=False),
        sa.Column("field_key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("confirmation_status", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source_urls", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("merchant_id", "field_key", name="uq_merchant_profile_field"),
    )
    op.create_index(
        "ix_merchant_profile_facts_merchant_id",
        "merchant_profile_facts",
        ["merchant_id"],
    )
    op.create_index(
        "ix_merchant_profile_facts_field_key",
        "merchant_profile_facts",
        ["field_key"],
    )
    op.add_column(
        "queries",
        sa.Column("intent_type", sa.String(length=20), nullable=False, server_default="recommendation"),
    )
    op.add_column(
        "queries",
        sa.Column("fact_keys", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "result_analyses",
        sa.Column("is_recommended", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("result_analyses", "is_recommended")
    op.drop_column("queries", "fact_keys")
    op.drop_column("queries", "intent_type")
    op.drop_index("ix_merchant_profile_facts_field_key", table_name="merchant_profile_facts")
    op.drop_index("ix_merchant_profile_facts_merchant_id", table_name="merchant_profile_facts")
    op.drop_table("merchant_profile_facts")

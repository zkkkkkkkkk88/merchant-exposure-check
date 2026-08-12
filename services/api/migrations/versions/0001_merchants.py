"""Create merchants and public sources."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_merchants"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "merchants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("normalized_name", sa.String(length=160), nullable=False),
        sa.Column("branch_name", sa.String(length=160), nullable=True),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("district", sa.String(length=80), nullable=True),
        sa.Column("industry", sa.String(length=80), nullable=False),
        sa.Column("address", sa.String(length=300), nullable=True),
        sa.Column("price_range", sa.String(length=80), nullable=True),
        sa.Column("opening_hours", sa.String(length=160), nullable=True),
        sa.Column("products", sa.JSON(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_merchants_city", "merchants", ["city"])
    op.create_index("ix_merchants_industry", "merchants", ["industry"])
    op.create_index("ix_merchants_normalized_name", "merchants", ["normalized_name"])
    op.create_table(
        "merchant_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("merchant_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("merchant_id", "url", name="uq_merchant_source_url"),
    )
    op.create_index("ix_merchant_sources_merchant_id", "merchant_sources", ["merchant_id"])


def downgrade() -> None:
    op.drop_index("ix_merchant_sources_merchant_id", table_name="merchant_sources")
    op.drop_table("merchant_sources")
    op.drop_index("ix_merchants_normalized_name", table_name="merchants")
    op.drop_index("ix_merchants_industry", table_name="merchants")
    op.drop_index("ix_merchants_city", table_name="merchants")
    op.drop_table("merchants")

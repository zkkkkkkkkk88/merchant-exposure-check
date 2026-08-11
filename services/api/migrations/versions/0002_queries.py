"""Create versioned query libraries."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_queries"
down_revision: str | None = "0001_merchants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "query_sets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("merchant_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("generator_name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("merchant_id", "version", name="uq_query_set_merchant_version"),
    )
    op.create_index("ix_query_sets_merchant_id", "query_sets", ["merchant_id"])
    op.create_table(
        "queries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("query_set_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.String(length=300), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=300), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("review_status", sa.String(length=20), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category IN ('geo', 'category', 'product', 'price', 'occasion', 'need')",
            name="ck_query_category",
        ),
        sa.CheckConstraint("priority BETWEEN 1 AND 5", name="ck_query_priority"),
        sa.CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected')",
            name="ck_query_review_status",
        ),
        sa.ForeignKeyConstraint(["query_set_id"], ["query_sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_queries_category", "queries", ["category"])
    op.create_index("ix_queries_query_set_id", "queries", ["query_set_id"])


def downgrade() -> None:
    op.drop_index("ix_queries_query_set_id", table_name="queries")
    op.drop_index("ix_queries_category", table_name="queries")
    op.drop_table("queries")
    op.drop_index("ix_query_sets_merchant_id", table_name="query_sets")
    op.drop_table("query_sets")

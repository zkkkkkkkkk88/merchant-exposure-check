"""add merchant local contexts

Revision ID: 0006_local_contexts
Revises: 0005_visibility_profiles
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_local_contexts"
down_revision = "0005_visibility_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "merchant_local_contexts",
        sa.Column("merchant_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("province", sa.String(length=80), nullable=True),
        sa.Column("city", sa.String(length=80), nullable=True),
        sa.Column("county", sa.String(length=80), nullable=True),
        sa.Column("township", sa.String(length=120), nullable=True),
        sa.Column("normalized_address", sa.String(length=400), nullable=True),
        sa.Column("landmarks", sa.JSON(), nullable=False),
        sa.Column("transport_options", sa.JSON(), nullable=False),
        sa.Column("source_urls", sa.JSON(), nullable=False),
        sa.Column("raw_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("merchant_id"),
    )
    op.create_index("ix_merchant_local_contexts_status", "merchant_local_contexts", ["status"])
    op.execute(
        sa.text(
            """
            INSERT INTO merchant_local_contexts
                (merchant_id, status, landmarks, transport_options, source_urls, created_at, updated_at)
            SELECT id, 'pending', '[]', '[]', '[]', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM merchants
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_merchant_local_contexts_status", table_name="merchant_local_contexts")
    op.drop_table("merchant_local_contexts")

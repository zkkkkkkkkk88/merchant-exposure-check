"""archive legacy query sets

Revision ID: 0008_query_set_archiving
Revises: 0007_mobile_checks
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_query_set_archiving"
down_revision = "0007_mobile_checks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "query_sets",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("query_sets", "is_archived")

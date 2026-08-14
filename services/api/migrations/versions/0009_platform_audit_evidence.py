"""store platform audit search evidence

Revision ID: 0009_platform_audit_evidence
Revises: 0008_platform_audits
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_platform_audit_evidence"
down_revision = "0008_platform_audits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "platform_audit_results",
        sa.Column("search_query", sa.Text(), nullable=True),
    )
    op.add_column(
        "platform_audit_results",
        sa.Column("baseline_fields", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("platform_audit_results", "baseline_fields")
    op.drop_column("platform_audit_results", "search_query")

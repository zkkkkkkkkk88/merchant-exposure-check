"""add platform information audits

Revision ID: 0008_platform_audits
Revises: 0008_query_set_archiving
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_platform_audits"
down_revision = "0008_query_set_archiving"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("platform_audit_runs", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("merchant_id", sa.Uuid(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), nullable=True), sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True), sa.Column("error_message", sa.Text(), nullable=True), sa.CheckConstraint("status IN ('queued','running','completed','partial','failed')", name="ck_platform_audit_run_status"), sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_platform_audit_runs_merchant_id", "platform_audit_runs", ["merchant_id"])
    op.create_index("ix_platform_audit_runs_status", "platform_audit_runs", ["status"])
    op.create_table("platform_audit_results", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("run_id", sa.Uuid(), nullable=False), sa.Column("platform_key", sa.String(50), nullable=False), sa.Column("platform_name", sa.String(100), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("found", sa.Boolean(), nullable=False), sa.Column("fields", sa.JSON(), nullable=False), sa.Column("issues", sa.JSON(), nullable=False), sa.Column("evidence", sa.JSON(), nullable=False), sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint("status IN ('complete','incomplete','conflict','not_found','needs_review')", name="ck_platform_audit_result_status"), sa.ForeignKeyConstraint(["run_id"], ["platform_audit_runs.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("run_id", "platform_key", name="uq_platform_audit_run_platform"))
    op.create_index("ix_platform_audit_results_run_id", "platform_audit_results", ["run_id"])


def downgrade() -> None:
    op.drop_table("platform_audit_results")
    op.drop_table("platform_audit_runs")

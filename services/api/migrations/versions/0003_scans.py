"""Create durable scan execution tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_scans"
down_revision: str | None = "0002_queries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scan_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("merchant_id", sa.Uuid(), nullable=False),
        sa.Column("query_set_id", sa.Uuid(), nullable=False),
        sa.Column("adapter_name", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'partial', 'failed')",
            name="ck_scan_run_status",
        ),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["query_set_id"], ["query_sets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_runs_merchant_id", "scan_runs", ["merchant_id"])
    op.create_index("ix_scan_runs_query_set_id", "scan_runs", ["query_set_id"])
    op.create_index("ix_scan_runs_status", "scan_runs", ["status"])

    op.create_table(
        "query_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_run_id", sa.Uuid(), nullable=False),
        sa.Column("query_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("adapter_name", sa.String(length=80), nullable=False),
        sa.Column("provider_request_id", sa.String(length=200), nullable=True),
        sa.Column("provider_metadata", sa.JSON(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('success', 'failed')", name="ck_query_result_status"),
        sa.ForeignKeyConstraint(["query_id"], ["queries.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scan_run_id"], ["scan_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scan_run_id", "query_id", name="uq_scan_result_query"),
    )
    op.create_index("ix_query_results_query_id", "query_results", ["query_id"])
    op.create_index("ix_query_results_scan_run_id", "query_results", ["scan_run_id"])

    op.create_table(
        "citations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("query_result_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["query_result_id"], ["query_results.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_citations_domain", "citations", ["domain"])
    op.create_index("ix_citations_query_result_id", "citations", ["query_result_id"])


def downgrade() -> None:
    op.drop_index("ix_citations_query_result_id", table_name="citations")
    op.drop_index("ix_citations_domain", table_name="citations")
    op.drop_table("citations")
    op.drop_index("ix_query_results_scan_run_id", table_name="query_results")
    op.drop_index("ix_query_results_query_id", table_name="query_results")
    op.drop_table("query_results")
    op.drop_index("ix_scan_runs_status", table_name="scan_runs")
    op.drop_index("ix_scan_runs_query_set_id", table_name="scan_runs")
    op.drop_index("ix_scan_runs_merchant_id", table_name="scan_runs")
    op.drop_table("scan_runs")

"""Add analysis and reporting records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_analysis"
down_revision: str | None = "0003_scans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "result_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("query_result_id", sa.Uuid(), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column("has_explicit_ranking", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("extraction_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["query_result_id"], ["query_results.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("query_result_id", name="uq_result_analysis_result"),
    )
    op.create_index("ix_result_analyses_query_result_id", "result_analyses", ["query_result_id"])
    op.create_table(
        "brand_mentions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("raw_name", sa.String(length=200), nullable=False),
        sa.Column("normalized_name", sa.String(length=200), nullable=False),
        sa.Column("is_target", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("recommendation_reason", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["result_analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("analysis_id", "brand_id", "normalized_name", "is_target"):
        op.create_index(f"ix_brand_mentions_{column}", "brand_mentions", [column])
    op.create_table(
        "extracted_facts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("normalized_brand_name", sa.String(length=200), nullable=False),
        sa.Column("is_target", sa.Boolean(), nullable=False),
        sa.Column("fact_type", sa.String(length=80), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("citation_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["analysis_id"], ["result_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["citation_id"], ["citations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("analysis_id", "brand_id", "is_target", "fact_type"):
        op.create_index(f"ix_extracted_facts_{column}", "extracted_facts", [column])
    op.create_table(
        "manual_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_run_id", sa.Uuid(), nullable=False),
        sa.Column("query_id", sa.Uuid(), nullable=False),
        sa.Column("answer_summary", sa.Text(), nullable=False),
        sa.Column("mentioned", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["query_id"], ["queries.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scan_run_id"], ["scan_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manual_checks_query_id", "manual_checks", ["query_id"])
    op.create_index("ix_manual_checks_scan_run_id", "manual_checks", ["scan_run_id"])
    op.create_table(
        "gap_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_run_id", sa.Uuid(), nullable=False),
        sa.Column("finding_type", sa.String(length=80), nullable=False),
        sa.Column("field", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("certainty", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["scan_run_id"], ["scan_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gap_findings_scan_run_id", "gap_findings", ["scan_run_id"])
    op.create_table(
        "finding_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("query_result_id", sa.Uuid(), nullable=False),
        sa.Column("citation_id", sa.Uuid(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["gap_findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["query_result_id"], ["query_results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["citation_id"], ["citations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finding_evidence_finding_id", "finding_evidence", ["finding_id"])
    op.create_index(
        "ix_finding_evidence_query_result_id", "finding_evidence", ["query_result_id"]
    )
    op.create_table(
        "action_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["gap_findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_action_items_finding_id", "action_items", ["finding_id"])


def downgrade() -> None:
    op.drop_table("action_items")
    op.drop_table("finding_evidence")
    op.drop_table("gap_findings")
    op.drop_table("manual_checks")
    op.drop_table("extracted_facts")
    op.drop_table("brand_mentions")
    op.drop_table("result_analyses")

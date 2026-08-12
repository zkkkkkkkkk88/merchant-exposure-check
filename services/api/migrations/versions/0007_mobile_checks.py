"""add mobile doubao validation records

Revision ID: 0007_mobile_checks
Revises: 0006_local_contexts
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_mobile_checks"
down_revision = "0006_local_contexts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("mobile_validation_sets", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("merchant_id", sa.Uuid(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_mobile_validation_sets_merchant_id", "mobile_validation_sets", ["merchant_id"])
    op.create_table("mobile_validation_items", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("validation_set_id", sa.Uuid(), nullable=False), sa.Column("query_id", sa.Uuid(), nullable=False), sa.Column("position", sa.Integer(), nullable=False), sa.ForeignKeyConstraint(["query_id"], ["queries.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["validation_set_id"], ["mobile_validation_sets.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("validation_set_id", "query_id", name="uq_mobile_validation_query"))
    op.create_index("ix_mobile_validation_items_validation_set_id", "mobile_validation_items", ["validation_set_id"])
    op.create_index("ix_mobile_validation_items_query_id", "mobile_validation_items", ["query_id"])
    op.create_table("mobile_check_rounds", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("merchant_id", sa.Uuid(), nullable=False), sa.Column("validation_set_id", sa.Uuid(), nullable=False), sa.Column("status", sa.String(length=20), nullable=False), sa.Column("location_text", sa.String(length=300), nullable=True), sa.Column("web_search_enabled", sa.Boolean(), nullable=False), sa.Column("raw_qa_text", sa.Text(), nullable=False), sa.Column("inherited_source_round_id", sa.Uuid(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True), sa.CheckConstraint("status IN ('draft', 'confirmed')", name="ck_mobile_round_status"), sa.ForeignKeyConstraint(["inherited_source_round_id"], ["mobile_check_rounds.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["validation_set_id"], ["mobile_validation_sets.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_mobile_check_rounds_merchant_id", "mobile_check_rounds", ["merchant_id"])
    op.create_index("ix_mobile_check_rounds_validation_set_id", "mobile_check_rounds", ["validation_set_id"])
    op.create_table("mobile_check_results", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("round_id", sa.Uuid(), nullable=False), sa.Column("validation_item_id", sa.Uuid(), nullable=False), sa.Column("mention_level", sa.String(length=20), nullable=False), sa.Column("competitors", sa.JSON(), nullable=False), sa.Column("information_accurate", sa.Boolean(), nullable=True), sa.Column("is_confirmed", sa.Boolean(), nullable=False), sa.Column("answer_excerpt", sa.Text(), nullable=True), sa.CheckConstraint("mention_level IN ('none', 'supplementary', 'primary')", name="ck_mobile_mention_level"), sa.ForeignKeyConstraint(["round_id"], ["mobile_check_rounds.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["validation_item_id"], ["mobile_validation_items.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("round_id", "validation_item_id", name="uq_mobile_round_item"))
    op.create_index("ix_mobile_check_results_round_id", "mobile_check_results", ["round_id"])
    op.create_index("ix_mobile_check_results_validation_item_id", "mobile_check_results", ["validation_item_id"])
    op.create_table("mobile_round_sources", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("round_id", sa.Uuid(), nullable=False), sa.Column("title", sa.String(length=500), nullable=False), sa.Column("url", sa.String(length=2048), nullable=True), sa.Column("domain", sa.String(length=255), nullable=True), sa.Column("source_type", sa.String(length=30), nullable=False), sa.Column("entity_name", sa.String(length=300), nullable=False), sa.Column("facts", sa.JSON(), nullable=False), sa.Column("evidence_kind", sa.String(length=30), nullable=False), sa.Column("access_status", sa.String(length=30), nullable=False), sa.Column("is_confirmed", sa.Boolean(), nullable=False), sa.CheckConstraint("source_type IN ('profile', 'registry', 'recruitment', 'douyin', 'local_media', 'government', 'industry', 'other')", name="ck_mobile_source_type"), sa.CheckConstraint("evidence_kind IN ('self_reported', 'official', 'third_party')", name="ck_mobile_evidence_kind"), sa.CheckConstraint("access_status IN ('maintainable', 'correctable', 'reference', 'unknown')", name="ck_mobile_access_status"), sa.ForeignKeyConstraint(["round_id"], ["mobile_check_rounds.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_mobile_round_sources_round_id", "mobile_round_sources", ["round_id"])
    op.create_table("mobile_evidence", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("round_id", sa.Uuid(), nullable=False), sa.Column("original_name", sa.String(length=500), nullable=False), sa.Column("storage_path", sa.String(length=1000), nullable=False), sa.Column("content_type", sa.String(length=100), nullable=False), sa.Column("size_bytes", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["round_id"], ["mobile_check_rounds.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_mobile_evidence_round_id", "mobile_evidence", ["round_id"])


def downgrade() -> None:
    op.drop_table("mobile_evidence")
    op.drop_table("mobile_round_sources")
    op.drop_table("mobile_check_results")
    op.drop_table("mobile_check_rounds")
    op.drop_table("mobile_validation_items")
    op.drop_table("mobile_validation_sets")

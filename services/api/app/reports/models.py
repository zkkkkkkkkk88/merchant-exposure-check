from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ManualCheck(Base):
    __tablename__ = "manual_checks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    scan_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("scan_runs.id", ondelete="CASCADE"), index=True
    )
    query_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("queries.id", ondelete="RESTRICT"), index=True
    )
    answer_summary: Mapped[str] = mapped_column(Text)
    mentioned: Mapped[bool] = mapped_column(Boolean)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sources: Mapped[list[str]] = mapped_column(JSON, default=list)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class GapFinding(Base):
    __tablename__ = "gap_findings"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    scan_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("scan_runs.id", ondelete="CASCADE"), index=True
    )
    finding_type: Mapped[str] = mapped_column(String(80))
    field: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(20))
    certainty: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)


class FindingEvidence(Base):
    __tablename__ = "finding_evidence"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    finding_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("gap_findings.id", ondelete="CASCADE"), index=True
    )
    query_result_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("query_results.id", ondelete="CASCADE"), index=True
    )
    citation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("citations.id", ondelete="SET NULL"), nullable=True
    )
    confidence: Mapped[float] = mapped_column(Float)


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    finding_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("gap_findings.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="open")

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class PlatformAuditRun(Base):
    __tablename__ = "platform_audit_runs"
    __table_args__ = (CheckConstraint("status IN ('queued','running','completed','partial','failed')", name="ck_platform_audit_run_status"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    platforms: Mapped[list[PlatformAuditResult]] = relationship(back_populates="run", cascade="all, delete-orphan", lazy="selectin")


class PlatformAuditResult(Base):
    __tablename__ = "platform_audit_results"
    __table_args__ = (
        UniqueConstraint("run_id", "platform_key", name="uq_platform_audit_run_platform"),
        CheckConstraint("status IN ('complete','incomplete','conflict','not_found','needs_review')", name="ck_platform_audit_result_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("platform_audit_runs.id", ondelete="CASCADE"), index=True)
    platform_key: Mapped[str] = mapped_column(String(50))
    platform_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20))
    found: Mapped[bool] = mapped_column(default=False)
    search_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    baseline_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    fields: Mapped[dict] = mapped_column(JSON, default=dict)
    issues: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence: Mapped[list[dict]] = mapped_column(JSON, default=list)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    run: Mapped[PlatformAuditRun] = relationship(back_populates="platforms")

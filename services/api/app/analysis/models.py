from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ResultAnalysis(Base):
    __tablename__ = "result_analyses"
    __table_args__ = (UniqueConstraint("query_result_id", name="uq_result_analysis_result"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    query_result_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("query_results.id", ondelete="CASCADE"), index=True
    )
    is_valid: Mapped[bool] = mapped_column(Boolean)
    has_explicit_ranking: Mapped[bool] = mapped_column(Boolean)
    confidence: Mapped[float] = mapped_column(Float)
    extraction_version: Mapped[str] = mapped_column(String(40), default="heuristic-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    mentions: Mapped[list[BrandMention]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", lazy="selectin"
    )
    facts: Mapped[list[ExtractedFactRecord]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", lazy="selectin"
    )


class BrandMention(Base):
    __tablename__ = "brand_mentions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("result_analyses.id", ondelete="CASCADE"), index=True
    )
    brand_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    raw_name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str] = mapped_column(String(200), index=True)
    is_target: Mapped[bool] = mapped_column(Boolean, index=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommendation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float)

    analysis: Mapped[ResultAnalysis] = relationship(back_populates="mentions")


class ExtractedFactRecord(Base):
    __tablename__ = "extracted_facts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("result_analyses.id", ondelete="CASCADE"), index=True
    )
    brand_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    normalized_brand_name: Mapped[str] = mapped_column(String(200))
    is_target: Mapped[bool] = mapped_column(Boolean, index=True)
    fact_type: Mapped[str] = mapped_column(String(80), index=True)
    value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    citation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("citations.id", ondelete="SET NULL"), nullable=True
    )

    analysis: Mapped[ResultAnalysis] = relationship(back_populates="facts")

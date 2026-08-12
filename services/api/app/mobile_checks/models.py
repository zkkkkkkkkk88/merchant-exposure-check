from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.queries.models import Query


def utc_now() -> datetime:
    return datetime.now(UTC)


class MobileValidationSet(Base):
    __tablename__ = "mobile_validation_sets"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    items: Mapped[list[MobileValidationItem]] = relationship(back_populates="validation_set", cascade="all, delete-orphan", lazy="selectin", order_by="MobileValidationItem.position")


class MobileValidationItem(Base):
    __tablename__ = "mobile_validation_items"
    __table_args__ = (UniqueConstraint("validation_set_id", "query_id", name="uq_mobile_validation_query"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    validation_set_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("mobile_validation_sets.id", ondelete="CASCADE"), index=True)
    query_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("queries.id", ondelete="RESTRICT"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    validation_set: Mapped[MobileValidationSet] = relationship(back_populates="items")
    query: Mapped[Query] = relationship(lazy="joined")


class MobileCheckRound(Base):
    __tablename__ = "mobile_check_rounds"
    __table_args__ = (CheckConstraint("status IN ('draft', 'confirmed')", name="ck_mobile_round_status"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    validation_set_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("mobile_validation_sets.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    location_text: Mapped[str | None] = mapped_column(String(300), nullable=True)
    web_search_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    raw_qa_text: Mapped[str] = mapped_column(Text, default="")
    inherited_source_round_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("mobile_check_rounds.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    results: Mapped[list[MobileCheckResult]] = relationship(back_populates="round", cascade="all, delete-orphan", lazy="selectin")
    sources: Mapped[list[MobileRoundSource]] = relationship(back_populates="round", cascade="all, delete-orphan", lazy="selectin")
    evidence: Mapped[list[MobileEvidence]] = relationship(back_populates="round", cascade="all, delete-orphan", lazy="selectin")


class MobileCheckResult(Base):
    __tablename__ = "mobile_check_results"
    __table_args__ = (
        UniqueConstraint("round_id", "validation_item_id", name="uq_mobile_round_item"),
        CheckConstraint("mention_level IN ('none', 'supplementary', 'primary')", name="ck_mobile_mention_level"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    round_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("mobile_check_rounds.id", ondelete="CASCADE"), index=True)
    validation_item_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("mobile_validation_items.id", ondelete="RESTRICT"), index=True)
    mention_level: Mapped[str] = mapped_column(String(20), default="none")
    competitors: Mapped[list[str]] = mapped_column(JSON, default=list)
    information_accurate: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    answer_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    round: Mapped[MobileCheckRound] = relationship(back_populates="results")
    validation_item: Mapped[MobileValidationItem] = relationship(lazy="joined")


class MobileRoundSource(Base):
    __tablename__ = "mobile_round_sources"
    __table_args__ = (
        CheckConstraint("source_type IN ('profile', 'registry', 'recruitment', 'douyin', 'local_media', 'government', 'industry', 'other')", name="ck_mobile_source_type"),
        CheckConstraint("evidence_kind IN ('self_reported', 'official', 'third_party')", name="ck_mobile_evidence_kind"),
        CheckConstraint("access_status IN ('maintainable', 'correctable', 'reference', 'unknown')", name="ck_mobile_access_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    round_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("mobile_check_rounds.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str] = mapped_column(String(30))
    entity_name: Mapped[str] = mapped_column(String(300))
    facts: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_kind: Mapped[str] = mapped_column(String(30))
    access_status: Mapped[str] = mapped_column(String(30), default="unknown")
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    round: Mapped[MobileCheckRound] = relationship(back_populates="sources")


class MobileEvidence(Base):
    __tablename__ = "mobile_evidence"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    round_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("mobile_check_rounds.id", ondelete="CASCADE"), index=True)
    original_name: Mapped[str] = mapped_column(String(500))
    storage_path: Mapped[str] = mapped_column(String(1000))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    round: Mapped[MobileCheckRound] = relationship(back_populates="evidence")

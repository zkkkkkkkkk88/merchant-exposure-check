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
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class QuerySet(Base):
    __tablename__ = "query_sets"
    __table_args__ = (
        UniqueConstraint("merchant_id", "version", name="uq_query_set_merchant_version"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    generator_name: Mapped[str] = mapped_column(String(80))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    queries: Mapped[list[Query]] = relationship(
        back_populates="query_set",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Query.created_at",
    )


class Query(Base):
    __tablename__ = "queries"
    __table_args__ = (
        CheckConstraint("priority BETWEEN 1 AND 5", name="ck_query_priority"),
        CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected')",
            name="ck_query_review_status",
        ),
        CheckConstraint(
            "category IN ('geo', 'category', 'product', 'price', 'occasion', 'need')",
            name="ck_query_category",
        ),
        CheckConstraint(
            "intent_type IN ('recommendation', 'verification')",
            name="ck_query_intent_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    query_set_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("query_sets.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(20), index=True)
    reason: Mapped[str] = mapped_column(String(300))
    priority: Mapped[int] = mapped_column(Integer, default=2)
    intent_type: Mapped[str] = mapped_column(String(20), default="recommendation")
    fact_keys: Mapped[list[str]] = mapped_column(JSON, default=list)
    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    query_set: Mapped[QuerySet] = relationship(back_populates="queries")

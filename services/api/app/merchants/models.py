from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160))
    normalized_name: Mapped[str] = mapped_column(String(160), index=True)
    branch_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    city: Mapped[str] = mapped_column(String(80), index=True)
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
    industry: Mapped[str] = mapped_column(String(80), index=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    price_range: Mapped[str | None] = mapped_column(String(80), nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(String(160), nullable=True)
    products: Mapped[list[str]] = mapped_column(JSON, default=list)
    strengths: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    sources: Mapped[list[MerchantSource]] = relationship(
        back_populates="merchant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    profile_facts: Mapped[list[MerchantProfileFact]] = relationship(
        back_populates="merchant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    local_context: Mapped[MerchantLocalContext] = relationship(
        back_populates="merchant",
        cascade="all, delete-orphan",
        lazy="selectin",
        uselist=False,
    )


class MerchantSource(Base):
    __tablename__ = "merchant_sources"
    __table_args__ = (UniqueConstraint("merchant_id", "url", name="uq_merchant_source_url"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    url: Mapped[str] = mapped_column(String(2048))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    merchant: Mapped[Merchant] = relationship(back_populates="sources")


class MerchantProfileFact(Base):
    __tablename__ = "merchant_profile_facts"
    __table_args__ = (
        UniqueConstraint("merchant_id", "field_key", name="uq_merchant_profile_field"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), index=True
    )
    field_key: Mapped[str] = mapped_column(String(100), index=True)
    value: Mapped[object] = mapped_column(JSON)
    confirmation_status: Mapped[str] = mapped_column(String(20), default="pending")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_urls: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    merchant: Mapped[Merchant] = relationship(back_populates="profile_facts")


class MerchantLocalContext(Base):
    __tablename__ = "merchant_local_contexts"

    merchant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    province: Mapped[str | None] = mapped_column(String(80), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    county: Mapped[str | None] = mapped_column(String(80), nullable=True)
    township: Mapped[str | None] = mapped_column(String(120), nullable=True)
    normalized_address: Mapped[str | None] = mapped_column(String(400), nullable=True)
    landmarks: Mapped[list[str]] = mapped_column(JSON, default=list)
    transport_options: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_urls: Mapped[list[str]] = mapped_column(JSON, default=list)
    raw_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    merchant: Mapped[Merchant] = relationship(back_populates="local_context")

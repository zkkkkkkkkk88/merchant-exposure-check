from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlatformAuditAdoptRequest(BaseModel):
    field_key: str = Field(min_length=2, max_length=50)


class PlatformAuditResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    platform_key: str
    platform_name: str
    status: str
    found: bool
    search_query: str | None = None
    baseline_fields: dict = Field(default_factory=dict)
    fields: dict = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    checked_at: datetime


class PlatformAuditRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    merchant_id: UUID
    status: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    platforms: list[PlatformAuditResultRead] = Field(default_factory=list)

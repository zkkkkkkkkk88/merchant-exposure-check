from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.queries.schemas import QueryRead


class MobileValidationItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    query_id: UUID
    position: int
    query: QueryRead


class MobileValidationSetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    merchant_id: UUID
    created_at: datetime
    items: list[MobileValidationItemRead] = Field(default_factory=list)


class MobileResultCreate(BaseModel):
    validation_item_id: UUID
    mention_level: Literal["none", "supplementary", "primary"]
    competitors: list[str] = Field(default_factory=list)
    information_accurate: bool | None = None
    is_confirmed: bool = False
    answer_excerpt: str | None = Field(default=None, max_length=3000)


class MobileSourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: str | None = Field(default=None, max_length=2048)
    source_type: Literal["profile", "registry", "recruitment", "douyin", "local_media", "government", "industry", "other"]
    entity_name: str = Field(min_length=1, max_length=300)
    facts: list[str] = Field(default_factory=list)
    evidence_kind: Literal["self_reported", "official", "third_party"]
    access_status: Literal["maintainable", "correctable", "reference", "unknown"] = "unknown"
    is_confirmed: bool = False


class MobileRoundCreate(BaseModel):
    validation_set_id: UUID
    location_text: str | None = Field(default=None, max_length=300)
    web_search_enabled: bool = True
    raw_qa_text: str = Field(default="", max_length=100_000)
    inherited_source_round_id: UUID | None = None
    results: list[MobileResultCreate] = Field(default_factory=list)
    sources: list[MobileSourceCreate] = Field(default_factory=list)


class MobileRoundRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    merchant_id: UUID
    validation_set_id: UUID
    status: Literal["draft", "confirmed"]
    location_text: str | None
    web_search_enabled: bool
    raw_qa_text: str
    inherited_source_round_id: UUID | None
    created_at: datetime
    confirmed_at: datetime | None


class MobileEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    original_name: str
    content_type: str
    size_bytes: int
    created_at: datetime


class MobileWorkspaceRead(BaseModel):
    latestRoundId: str | None
    sourceRoundId: str | None
    metrics: dict | None
    entities: list[str]
    sourceGaps: list[dict]

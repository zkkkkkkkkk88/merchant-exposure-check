from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

QueryCategory = Literal["geo", "category", "product", "price", "occasion", "need"]
QueryIntent = Literal["recommendation", "verification"]


class QueryDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=2, max_length=300)
    category: QueryCategory
    reason: str = Field(min_length=2, max_length=300)
    priority: int = Field(ge=1, le=5)
    intent_type: QueryIntent = "recommendation"
    fact_keys: list[str] = Field(default_factory=list)


ReviewStatus = Literal["pending", "approved", "rejected"]


class QueryGenerateRequest(BaseModel):
    count: int = Field(default=15, ge=6, le=100)


class QueryUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=2, max_length=300)
    priority: int | None = Field(default=None, ge=1, le=5)
    review_status: ReviewStatus | None = None
    is_enabled: bool | None = None


class QueryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    query_set_id: UUID
    text: str
    category: QueryCategory
    reason: str
    priority: int
    intent_type: QueryIntent
    fact_keys: list[str]
    review_status: ReviewStatus
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class QuerySetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    version: int
    generator_name: str
    is_archived: bool
    created_at: datetime
    queries: list[QueryRead]


class QuerySetCleanupRead(BaseModel):
    deleted: int
    archived: int
    kept: int

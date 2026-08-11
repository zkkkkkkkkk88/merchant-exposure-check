from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

ScanStatus = Literal["queued", "running", "completed", "partial", "failed"]
ResultStatus = Literal["success", "failed"]


class ScanRunCreate(BaseModel):
    merchant_id: UUID
    query_set_id: UUID
    adapter_name: str = Field(min_length=1, max_length=80)


class ManualCitationCreate(BaseModel):
    url: HttpUrl
    title: str | None = Field(default=None, max_length=500)
    snippet: str | None = Field(default=None, max_length=2000)


class ManualResultCreate(BaseModel):
    query_id: UUID
    raw_text: str = Field(min_length=1)
    citations: list[ManualCitationCreate] = Field(default_factory=list)


class ManualResultsCreate(BaseModel):
    results: list[ManualResultCreate] = Field(min_length=1)


class CitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    domain: str
    title: str | None
    snippet: str | None


class QueryResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    query_id: UUID
    status: ResultStatus
    raw_text: str | None
    adapter_name: str
    provider_request_id: str | None
    attempt_count: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime
    citations: list[CitationRead]


class ScanRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    query_set_id: UUID
    adapter_name: str
    status: ScanStatus
    success_count: int
    failure_count: int
    error_summary: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    results: list[QueryResultRead]

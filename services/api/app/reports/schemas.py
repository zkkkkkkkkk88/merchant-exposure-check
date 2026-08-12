from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.analysis.contracts import MetricSnapshot


class ReportRead(BaseModel):
    merchant_id: UUID
    scan_run_id: UUID
    metrics: MetricSnapshot
    findings: list[dict] = Field(default_factory=list)


class HistoryRead(BaseModel):
    left: MetricSnapshot
    right: MetricSnapshot
    deltas: dict[str, Decimal]


class ManualCheckCreate(BaseModel):
    query_id: UUID
    answer_summary: str = Field(min_length=1, max_length=3000)
    mentioned: bool
    position: int | None = Field(default=None, ge=1)
    sources: list[HttpUrl] = Field(default_factory=list)

    @model_validator(mode="after")
    def position_requires_mention(self):
        if self.position is not None and not self.mentioned:
            raise ValueError("position requires mentioned=true")
        return self


class ManualCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scan_run_id: UUID
    query_id: UUID
    answer_summary: str
    mentioned: bool
    position: int | None
    sources: list[str]
    checked_at: datetime


class DashboardRead(BaseModel):
    merchant: dict[str, str | None]
    lastRunAt: datetime
    metrics: dict[str, Decimal | int | str]
    trend: list[dict[str, str | Decimal]]
    categories: list[dict[str, str | Decimal | int]]
    competitors: list[dict[str, object]]
    actions: list[dict[str, object]]

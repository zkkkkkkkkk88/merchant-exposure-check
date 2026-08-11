from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.queries.schemas import QueryCategory


class ExtractedMention(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_name: str = Field(min_length=1, max_length=200)
    position: int | None = Field(default=None, ge=1)
    recommendation_reason: str | None = Field(default=None, max_length=1000)
    confidence: float = Field(ge=0, le=1)
    citation_urls: list[str] = Field(default_factory=list)


class ExtractedFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_brand_name: str = Field(min_length=1, max_length=200)
    fact_type: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0, le=1)
    citation_urls: list[str] = Field(default_factory=list)


class ExtractionPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_valid: bool
    has_explicit_ranking: bool
    confidence: float = Field(ge=0, le=1)
    mentions: list[ExtractedMention] = Field(default_factory=list)
    facts: list[ExtractedFact] = Field(default_factory=list)


class MetricMention(BaseModel):
    model_config = ConfigDict(frozen=True)

    brand_id: UUID
    normalized_name: str = Field(min_length=1)
    position: int | None = Field(default=None, ge=1)


class AnalyzedQueryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    query_id: UUID
    category: QueryCategory
    is_valid: bool
    has_explicit_ranking: bool
    mentions: list[MetricMention]
    target_source_domains: set[str] = Field(default_factory=set)
    confirmed_target_fields: set[str] = Field(default_factory=set)


class MetricSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_query_count: int
    valid_query_count: int
    mention_rate: Decimal
    first_position_rate: Decimal
    task_valid_rate: Decimal
    source_coverage_rate: Decimal
    independent_source_count: int
    category_coverage: dict[str, Decimal]
    competitor_counts: dict[str, int]
    confirmed_target_fields: set[str]

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdapterError(RuntimeError):
    pass


class AdapterConfigurationError(AdapterError):
    pass


class RetryableAdapterError(AdapterError):
    pass


class AdapterResultNotFoundError(AdapterError):
    pass


class RawCitation(BaseModel):
    model_config = ConfigDict(frozen=True)

    url: str = Field(min_length=1, max_length=2048)
    title: str | None = Field(default=None, max_length=500)
    snippet: str | None = Field(default=None, max_length=2000)


class SearchRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str = Field(min_length=2, max_length=300)
    merchant_id: UUID
    correlation_id: str = Field(min_length=1, max_length=120)


class SearchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_text: str
    citations: list[RawCitation]
    provider_request_id: str | None = None


class SearchAdapter(Protocol):
    name: str

    async def search(self, request: SearchRequest) -> SearchResponse: ...

from uuid import uuid4

import httpx
import pytest

from app.scans.adapters.ark import ArkSearchAdapter
from app.scans.adapters.base import (
    AdapterConfigurationError,
    RetryableAdapterError,
    SearchRequest,
    SearchResponse,
)
from app.scans.adapters.manual import ManualSearchAdapter


@pytest.mark.asyncio
async def test_manual_adapter_returns_supplied_result() -> None:
    expected = SearchResponse(raw_text="推荐 O'eat。", citations=[])
    adapter = ManualSearchAdapter({"杭州约会餐厅推荐": expected})

    result = await adapter.search(
        SearchRequest(
            query="杭州约会餐厅推荐",
            merchant_id=uuid4(),
            correlation_id="q-1",
        )
    )

    assert result == expected


def test_ark_adapter_requires_server_side_key() -> None:
    with pytest.raises(AdapterConfigurationError, match="ARK_API_KEY"):
        ArkSearchAdapter(api_key="", model="doubao-test")


@pytest.mark.asyncio
async def test_ark_adapter_maps_response_text_and_citations() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer server-key"
        assert b'"type":"web_search"' in request.content
        return httpx.Response(
            200,
            json={
                "id": "response-1",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "推荐 O'eat。",
                                "annotations": [
                                    {
                                        "type": "url_citation",
                                        "url": "https://example.com/review",
                                        "title": "测评",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = ArkSearchAdapter(api_key="server-key", model="doubao-test", client=client)
        result = await adapter.search(
            SearchRequest(query="杭州餐厅推荐", merchant_id=uuid4(), correlation_id="q-1")
        )

    assert result.raw_text == "推荐 O'eat。"
    assert result.provider_request_id == "response-1"
    assert result.citations[0].url == "https://example.com/review"


@pytest.mark.asyncio
async def test_ark_adapter_marks_rate_limit_as_retryable() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(429, request=request))
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = ArkSearchAdapter(api_key="server-key", model="doubao-test", client=client)
        with pytest.raises(RetryableAdapterError, match="429"):
            await adapter.search(
                SearchRequest(query="杭州餐厅推荐", merchant_id=uuid4(), correlation_id="q-1")
            )

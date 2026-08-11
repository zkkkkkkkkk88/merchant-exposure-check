from collections.abc import Iterable

import httpx

from app.scans.adapters.base import (
    AdapterConfigurationError,
    RawCitation,
    RetryableAdapterError,
    SearchRequest,
    SearchResponse,
)


class ArkSearchAdapter:
    name = "ark"
    endpoint = "https://ark.cn-beijing.volces.com/api/v3/responses"

    def __init__(
        self,
        api_key: str,
        model: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise AdapterConfigurationError("ARK_API_KEY is required for the Ark adapter")
        self._api_key = api_key
        self._model = model
        self._client = client

    async def search(self, request: SearchRequest) -> SearchResponse:
        payload = {
            "model": self._model,
            "input": request.query,
            "tools": [{"type": "web_search"}],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-Correlation-ID": request.correlation_id,
        }
        try:
            if self._client is not None:
                response = await self._client.post(self.endpoint, json=payload, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.post(self.endpoint, json=payload, headers=headers)
            response.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException) as error:
            raise RetryableAdapterError(str(error)) from error
        except httpx.HTTPStatusError as error:
            status_code = error.response.status_code
            if status_code == 429 or status_code >= 500:
                raise RetryableAdapterError(f"Ark request failed with HTTP {status_code}") from error
            raise
        data = response.json()
        return SearchResponse(
            raw_text=self._extract_text(data.get("output", [])),
            citations=self._extract_citations(data.get("output", [])),
            provider_request_id=data.get("id") or response.headers.get("x-request-id"),
        )

    @staticmethod
    def _content_items(output: Iterable[dict]) -> Iterable[dict]:
        for item in output:
            if item.get("type") == "message":
                yield from item.get("content", [])

    @classmethod
    def _extract_text(cls, output: Iterable[dict]) -> str:
        return "\n".join(
            content.get("text", "")
            for content in cls._content_items(output)
            if content.get("type") in {"output_text", "text"} and content.get("text")
        )

    @classmethod
    def _extract_citations(cls, output: Iterable[dict]) -> list[RawCitation]:
        citations: list[RawCitation] = []
        seen: set[str] = set()
        for content in cls._content_items(output):
            for annotation in content.get("annotations", []):
                detail = annotation.get("url_citation", annotation)
                url = detail.get("url")
                if not url or url in seen:
                    continue
                seen.add(url)
                citations.append(
                    RawCitation(
                        url=url,
                        title=detail.get("title"),
                        snippet=detail.get("snippet"),
                    )
                )
        return citations

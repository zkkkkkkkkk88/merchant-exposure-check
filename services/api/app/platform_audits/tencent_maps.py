from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import httpx

TENCENT_PLACE_SEARCH_URL = "https://apis.map.qq.com/ws/place/v1/search"


@dataclass(frozen=True)
class TencentMapLookup:
    found: bool
    fields: dict[str, Any]
    evidence: list[dict[str, Any]]


def _normalized_name(value: str) -> str:
    return "".join(character.casefold() for character in value if character.isalnum())


def _name_score(expected: str, candidate: str) -> float:
    expected_normalized = _normalized_name(expected)
    candidate_normalized = _normalized_name(candidate)
    if not expected_normalized or not candidate_normalized:
        return 0.0
    if expected_normalized in candidate_normalized or candidate_normalized in expected_normalized:
        return 1.0
    return SequenceMatcher(None, expected_normalized, candidate_normalized).ratio()


class TencentMapClient:
    def __init__(
        self,
        api_key: str,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.api_key = api_key
        self.http_client = http_client
        self.timeout_seconds = timeout_seconds

    async def lookup(
        self,
        *,
        merchant_name: str,
        city: str,
        district: str | None,
    ) -> TencentMapLookup:
        params = {
            "boundary": f"region({city},0)",
            "keyword": merchant_name,
            "page_size": "10",
            "page_index": "1",
            "orderby": "_distance",
            "key": self.api_key,
        }
        try:
            if self.http_client is None:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.get(TENCENT_PLACE_SEARCH_URL, params=params)
            else:
                response = await self.http_client.get(TENCENT_PLACE_SEARCH_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError("腾讯地图网络请求失败") from exc
        payload = response.json()
        if payload.get("status") != 0:
            message = payload.get("message") or "腾讯地图接口返回失败"
            raise RuntimeError(f"腾讯地图接口返回失败：{message}")

        candidates = payload.get("data") or []
        if not isinstance(candidates, list):
            raise TypeError("腾讯地图接口返回的数据格式不正确")

        ranked = sorted(
            (candidate for candidate in candidates if isinstance(candidate, dict)),
            key=lambda candidate: _name_score(merchant_name, str(candidate.get("title", ""))),
            reverse=True,
        )
        if not ranked or _name_score(merchant_name, str(ranked[0].get("title", ""))) < 0.55:
            return TencentMapLookup(found=False, fields={}, evidence=[])

        place = ranked[0]
        fields = {
            key: value
            for key, value in {
                "name": place.get("title"),
                "address": place.get("address"),
                "phone": place.get("tel"),
            }.items()
            if value not in (None, "", [])
        }
        location = place.get("location") or {}
        evidence = [
            {
                "url": "https://map.qq.com/",
                "title": f"腾讯地图：{place.get('title') or merchant_name}",
                "snippet": place.get("address") or district or city,
                "poi_id": str(place.get("id") or ""),
                "location": {
                    key: location[key]
                    for key in ("lat", "lng")
                    if key in location
                },
            }
        ]
        return TencentMapLookup(found=True, fields=fields, evidence=evidence)

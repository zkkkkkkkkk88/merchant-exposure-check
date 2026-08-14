from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import httpx

AMAP_PLACE_SEARCH_URL = "https://restapi.amap.com/v3/place/text"


@dataclass(frozen=True)
class AmapLookup:
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


class AmapClient:
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
    ) -> AmapLookup:
        params = {
            "keywords": merchant_name,
            "city": city,
            "citylimit": "true",
            "offset": "10",
            "page": "1",
            "extensions": "all",
            "key": self.api_key,
        }
        try:
            if self.http_client is None:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.get(AMAP_PLACE_SEARCH_URL, params=params)
            else:
                response = await self.http_client.get(AMAP_PLACE_SEARCH_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError("高德地图网络请求失败") from exc

        payload = response.json()
        if payload.get("status") != "1":
            message = payload.get("info") or "高德地图接口返回失败"
            raise RuntimeError(f"高德地图接口返回失败：{message}")
        candidates = payload.get("pois") or []
        if not isinstance(candidates, list):
            raise TypeError("高德地图接口返回的数据格式不正确")
        ranked = sorted(
            (candidate for candidate in candidates if isinstance(candidate, dict)),
            key=lambda candidate: _name_score(merchant_name, str(candidate.get("name", ""))),
            reverse=True,
        )
        if not ranked or _name_score(merchant_name, str(ranked[0].get("name", ""))) < 0.55:
            return AmapLookup(found=False, fields={}, evidence=[])

        place = ranked[0]
        fields = {
            key: value
            for key, value in {
                "name": place.get("name"),
                "address": place.get("address"),
                "phone": place.get("tel"),
            }.items()
            if value not in (None, "", []) and isinstance(value, str)
        }
        poi_id = str(place.get("id") or "")
        location = str(place.get("location") or "")
        longitude, separator, latitude = location.partition(",")
        evidence = [
            {
                "url": f"https://www.amap.com/place/{poi_id}" if poi_id else "https://www.amap.com/",
                "title": f"高德地图：{place.get('name') or merchant_name}",
                "snippet": place.get("address") or district or city,
                "poi_id": poi_id,
                "location": (
                    {"lng": float(longitude), "lat": float(latitude)}
                    if separator and longitude and latitude
                    else {}
                ),
            }
        ]
        return AmapLookup(found=True, fields=fields, evidence=evidence)

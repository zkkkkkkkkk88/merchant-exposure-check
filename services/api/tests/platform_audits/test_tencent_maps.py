import httpx
import pytest

from app.platform_audits.tencent_maps import TencentMapClient


@pytest.mark.asyncio
async def test_tencent_map_client_returns_matching_place_without_leaking_key() -> None:
    seen_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(
            200,
            json={
                "status": 0,
                "message": "query ok",
                "data": [
                    {
                        "id": "123456",
                        "title": "澜沧皓雅口腔门诊部",
                        "address": "云南省普洱市澜沧拉祜族自治县",
                        "tel": "0879-1234567",
                        "category": "医疗保健服务:专科医院:口腔医院",
                        "location": {"lat": 22.55, "lng": 99.93},
                    }
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TencentMapClient("top-secret", http_client=http_client)
        result = await client.lookup(
            merchant_name="澜沧皓雅口腔门诊部",
            city="普洱市",
            district="澜沧拉祜族自治县",
        )

    assert result.found is True
    assert result.fields == {
        "name": "澜沧皓雅口腔门诊部",
        "address": "云南省普洱市澜沧拉祜族自治县",
        "phone": "0879-1234567",
    }
    assert result.evidence[0]["title"] == "腾讯地图：澜沧皓雅口腔门诊部"
    assert result.evidence[0]["poi_id"] == "123456"
    assert "top-secret" not in str(result.evidence)
    assert seen_request is not None
    assert seen_request.url.params["boundary"] == "region(普洱市,0)"
    assert seen_request.url.params["keyword"] == "澜沧皓雅口腔门诊部"


@pytest.mark.asyncio
async def test_tencent_map_client_reports_api_errors_without_exposing_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": 110, "message": "请求来源未被授权"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TencentMapClient("top-secret", http_client=http_client)
        with pytest.raises(RuntimeError, match="请求来源未被授权") as error:
            await client.lookup(
                merchant_name="澜沧皓雅口腔门诊部",
                city="普洱市",
                district="澜沧拉祜族自治县",
            )

    assert "top-secret" not in str(error.value)

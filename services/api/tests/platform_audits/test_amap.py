import httpx
import pytest

from app.platform_audits.amap import AmapClient


@pytest.mark.asyncio
async def test_amap_client_returns_matching_place_without_leaking_key() -> None:
    seen_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(
            200,
            json={
                "status": "1",
                "info": "OK",
                "pois": [
                    {
                        "id": "B0LGP5LEQB",
                        "name": "澜沧皓雅口腔门诊部",
                        "address": "芦笙路郑建周家综合楼S-102-103",
                        "tel": "0879-7594999",
                        "location": "99.933322,22.550327",
                    }
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = AmapClient("top-secret", http_client=http_client)
        result = await client.lookup(
            merchant_name="澜沧皓雅口腔门诊部",
            city="普洱市",
            district="澜沧拉祜族自治县",
        )

    assert result.found is True
    assert result.fields == {
        "name": "澜沧皓雅口腔门诊部",
        "address": "芦笙路郑建周家综合楼S-102-103",
        "phone": "0879-7594999",
    }
    assert result.evidence[0]["url"] == "https://www.amap.com/place/B0LGP5LEQB"
    assert result.evidence[0]["poi_id"] == "B0LGP5LEQB"
    assert "top-secret" not in str(result.evidence)
    assert seen_request is not None
    assert seen_request.url.params["keywords"] == "澜沧皓雅口腔门诊部"
    assert seen_request.url.params["city"] == "普洱市"
    assert seen_request.url.params["citylimit"] == "true"


@pytest.mark.asyncio
async def test_amap_client_reports_api_errors_without_exposing_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"status": "0", "info": "INVALID_USER_KEY", "infocode": "10001"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = AmapClient("top-secret", http_client=http_client)
        with pytest.raises(RuntimeError, match="INVALID_USER_KEY") as error:
            await client.lookup(
                merchant_name="澜沧皓雅口腔门诊部",
                city="普洱市",
                district="澜沧拉祜族自治县",
            )

    assert "top-secret" not in str(error.value)

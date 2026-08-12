from uuid import uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.merchants.local_context import parse_local_context, process_next_local_context
from app.merchants.schemas import MerchantCreate
from app.merchants.service import MerchantService
from app.scans.adapters.base import RawCitation, SearchRequest, SearchResponse


def test_parse_local_context_prefers_explicit_county_and_keeps_only_returned_facts() -> None:
    parsed = parse_local_context(
        '```json\n{"province":"云南省","city":"普洱市","county":"澜沧县","township":"勐朗镇","normalized_address":"澜沧县勐朗镇东朗路1号","landmarks":["东朗路"],"transport_options":["步行"]}\n```'
    )
    assert parsed.county == "澜沧县"
    assert parsed.city == "普洱市"
    assert parsed.landmarks == ["东朗路"]


def test_parse_local_context_rejects_non_json_answer() -> None:
    with pytest.raises(ValueError, match="JSON"):
        parse_local_context("澜沧县大概位于普洱市")


class FakeContextAdapter:
    name = "ark"

    async def search(self, request: SearchRequest) -> SearchResponse:
        assert "县、自治县或县级市" in request.query
        return SearchResponse(
            raw_text='{"province":"云南省","city":"普洱市","county":"澜沧县","township":"勐朗镇","normalized_address":"云南省普洱市澜沧县勐朗镇东朗路1号","landmarks":[],"transport_options":[]}',
            citations=[RawCitation(url="https://www.lancang.gov.cn/address", title="澜沧县")],
        )


@pytest.mark.asyncio
async def test_worker_resolves_pending_context_with_citations(db_session: Session) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="县城门诊", city="云南", district="普洱市", industry="口腔医疗机构", address="澜沧县勐朗镇东朗路1号"),
    )
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)

    processed = await process_next_local_context(factory, FakeContextAdapter())

    assert processed == merchant.id
    db_session.expire_all()
    refreshed = MerchantService.get(db_session, merchant.id)
    assert refreshed.local_context.status == "completed", refreshed.local_context.error_message
    assert refreshed.local_context.county == "澜沧县"
    assert refreshed.local_context.source_urls == ["https://www.lancang.gov.cn/address"]

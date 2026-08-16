import pytest
from sqlalchemy.orm import Session

from app.mobile_checks.schemas import CompetitorOccurrence
from app.mobile_checks.schemas import MobileSourceDiscoveryCreate
from app.mobile_checks.source_discovery import (
    MobileSourceDiscoveryService,
    select_discovery_entities,
)
from app.platform_audits.models import PlatformAuditResult, PlatformAuditRun
from app.scans.adapters.base import RawCitation, SearchRequest, SearchResponse
from tests.mobile_checks.test_service import add_merchant


class FakeSearchAdapter:
    name = "fake"

    def __init__(self) -> None:
        self.calls: list[SearchRequest] = []

    async def search(self, request: SearchRequest) -> SearchResponse:
        self.calls.append(request)
        if "失败诊所" in request.query:
            raise RuntimeError("network unavailable")
        entity = "王天佑口腔诊所" if "王天佑" in request.query else "澜沧皓雅口腔门诊部"
        return SearchResponse(
            raw_text="",
            citations=[
                RawCitation(url="https://existing.example/profile", title=f"{entity}旧页面", snippet="重复"),
                RawCitation(url=f"https://map.example/{entity}", title=f"{entity}地图", snippet="地址和电话"),
                RawCitation(url=f"https://jobs.example/{entity}", title=f"{entity}招聘", snippet="设备与招聘"),
                RawCitation(url=f"https://news.example/{entity}", title=f"{entity}报道", snippet="公开报道"),
                RawCitation(url="ftp://invalid.example/file", title="无效地址"),
            ],
        )


def test_select_discovery_entities_keeps_target_and_recurring_competitors() -> None:
    selected = select_discovery_entities(
        "澜沧皓雅口腔门诊部",
        [
            CompetitorOccurrence(name="王天佑口腔诊所", occurrence_count=3),
            CompetitorOccurrence(name="福康口腔", occurrence_count=2),
            CompetitorOccurrence(name="偶发诊所", occurrence_count=1),
            CompetitorOccurrence(name="德玉口腔", occurrence_count=2),
            CompetitorOccurrence(name="第五家", occurrence_count=3),
            CompetitorOccurrence(name="澜沧皓雅口腔门诊部", occurrence_count=3),
        ],
    )

    assert selected == [
        "澜沧皓雅口腔门诊部",
        "王天佑口腔诊所",
        "第五家",
        "福康口腔",
    ]


@pytest.mark.asyncio
async def test_discovery_reuses_audit_and_limits_search_results(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    audit = PlatformAuditRun(merchant_id=merchant.id, status="completed")
    db_session.add(audit)
    db_session.flush()
    db_session.add(
        PlatformAuditResult(
            run_id=audit.id,
            platform_key="official_web",
            platform_name="官网",
            status="complete",
            found=True,
            evidence=[
                {
                    "url": "https://existing.example/profile",
                    "title": "机构公开主页",
                    "snippet": "地址、电话",
                }
            ],
        )
    )
    db_session.commit()
    adapter = FakeSearchAdapter()

    result = await MobileSourceDiscoveryService(db_session, adapter).discover(
        merchant.id,
        MobileSourceDiscoveryCreate(
            location_text="澜沧县",
            competitors=[
                CompetitorOccurrence(name="王天佑口腔诊所", occurrence_count=3),
                CompetitorOccurrence(name="失败诊所", occurrence_count=2),
                CompetitorOccurrence(name="偶发诊所", occurrence_count=1),
            ],
        ),
    )

    assert [group.entity_name for group in result.groups] == [
        merchant.name,
        "王天佑口腔诊所",
        "失败诊所",
    ]
    assert result.external_call_count == 3
    assert len(result.groups[0].sources) == 3
    assert result.groups[0].sources[0].reused_from_audit is True
    assert len({source.url for source in result.groups[0].sources}) == 3
    assert len(result.groups[1].sources) == 3
    assert result.groups[2].sources == []
    assert result.groups[2].error == "本次检索未完成"
    assert all(source.url.startswith("https://") for group in result.groups for source in group.sources)


@pytest.mark.asyncio
async def test_discovery_skips_target_search_when_audit_has_three_sources(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    audit = PlatformAuditRun(merchant_id=merchant.id, status="partial")
    db_session.add(audit)
    db_session.flush()
    db_session.add(
        PlatformAuditResult(
            run_id=audit.id,
            platform_key="official_web",
            platform_name="官网",
            status="complete",
            found=True,
            evidence=[
                {"url": f"https://source{index}.example/page", "title": f"来源{index}"}
                for index in range(3)
            ],
        )
    )
    db_session.commit()
    adapter = FakeSearchAdapter()

    result = await MobileSourceDiscoveryService(db_session, adapter).discover(
        merchant.id,
        MobileSourceDiscoveryCreate(),
    )

    assert len(result.groups[0].sources) == 3
    assert result.external_call_count == 0
    assert adapter.calls == []

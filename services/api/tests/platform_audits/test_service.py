from uuid import uuid4

from sqlalchemy.orm import Session

import pytest

from app.merchants.models import Merchant, MerchantProfileFact
from app.platform_audits.service import (
    PlatformAuditAdoptionConflict,
    PlatformAuditAdoptionInvalid,
    PlatformAuditResultNotFound,
    PlatformAuditService,
    classify_platform,
)


def add_merchant(session: Session, *, name: str = "澜沧皓雅口腔门诊部") -> Merchant:
    merchant = Merchant(id=uuid4(), name=name, normalized_name=name, city="澜沧县", industry="口腔医疗", address="勐朗镇", opening_hours="09:00-18:00", products=["正畸", "补牙"])
    session.add(merchant)
    session.commit()
    return merchant


def test_classify_platform_treats_new_public_fields_as_successful_discoveries() -> None:
    assert classify_platform(
        {"name": "澜沧皓雅口腔门诊部", "phone": None},
        {"name": "澜沧皓雅口腔门诊部", "phone": "0879-1"},
        True,
    ) == ("complete", ["发现可补录电话：0879-1"])


def test_classify_platform_detects_conflicts_and_missing_fields() -> None:
    assert classify_platform({"name": "澜沧皓雅口腔门诊部", "address": "勐朗镇"}, {"name": "皓雅口腔", "address": "勐朗镇"}, True)[0] == "conflict"
    assert classify_platform({"name": "澜沧皓雅口腔门诊部", "products": ["正畸"]}, {"name": "澜沧皓雅口腔门诊部", "products": []}, True)[0] == "incomplete"
    assert classify_platform({"name": "澜沧皓雅口腔门诊部"}, {}, False)[0] == "not_found"


def test_classify_platform_accepts_an_address_with_a_region_prefix() -> None:
    status, issues = classify_platform(
        {
            "name": "澜沧皓雅口腔门诊部",
            "address": "郑建周家综合楼S-101S-102跟二层",
            "phone": None,
        },
        {
            "name": "澜沧皓雅口腔门诊部",
            "address": "澜沧拉祜族自治县郑建周家综合楼S-101S-102跟二层",
            "phone": "0879-7594999",
        },
        True,
    )

    assert status == "complete"
    assert issues == ["发现可补录电话：0879-7594999"]


def test_classify_platform_keeps_discoveries_when_other_fields_are_missing() -> None:
    status, issues = classify_platform(
        {"name": "测试商家", "phone": None, "opening_hours": "09:00-18:00"},
        {"name": "测试商家", "phone": "0879-1"},
        True,
    )

    assert status == "incomplete"
    assert issues == ["信息不完整：营业时间", "发现可补录电话：0879-1"]


def test_platform_audit_run_is_isolated_and_aggregates_results(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    other = add_merchant(db_session, name="其他商家")
    service = PlatformAuditService(db_session)
    run = service.create_run(merchant.id)
    service.record_platform(run.id, "amap", "高德地图", found=True, fields={"name": merchant.name, "address": merchant.address, "products": []}, evidence=[{"url": "https://example.com/amap", "title": "高德商户页"}], search_query="澜沧皓雅口腔门诊部 高德地图")

    latest = service.get_latest(merchant.id)

    assert latest is not None
    assert latest.platforms[0].status == "incomplete"
    assert latest.platforms[0].evidence[0]["url"] == "https://example.com/amap"
    assert latest.platforms[0].search_query == "澜沧皓雅口腔门诊部 高德地图"
    assert latest.platforms[0].baseline_fields == {
        "name": merchant.name,
        "address": merchant.address,
        "opening_hours": merchant.opening_hours,
        "products": merchant.products,
    }
    assert service.get_latest(other.id) is None


def test_create_run_reuses_the_active_run(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    service = PlatformAuditService(db_session)

    first = service.create_run(merchant.id)
    second = service.create_run(merchant.id)

    assert second.id == first.id


def test_adopt_platform_field_creates_a_confirmed_sourced_profile_fact(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    service = PlatformAuditService(db_session)
    run = service.create_run(merchant.id)
    result = service.record_platform(
        run.id,
        "amap",
        "高德地图",
        found=True,
        fields={"name": merchant.name, "address": merchant.address, "phone": "0879-7594999"},
        evidence=[{"url": "https://www.amap.com/place/example", "title": "高德地图商户页"}],
        search_query=f"{merchant.name} 高德地图",
    )
    run.status = "completed"
    db_session.commit()

    adopted = service.adopt_field(merchant.id, result.id, "phone")
    repeated = service.adopt_field(merchant.id, result.id, "phone")

    facts = db_session.query(MerchantProfileFact).filter_by(merchant_id=merchant.id, field_key="contact.phone").all()
    assert len(facts) == 1
    assert facts[0].value == "0879-7594999"
    assert facts[0].confirmation_status == "confirmed"
    assert facts[0].source_urls == ["https://www.amap.com/place/example"]
    assert repeated.id == adopted.id
    assert adopted.baseline_fields["phone"] == "0879-7594999"
    assert all("发现可补录电话" not in issue for issue in adopted.issues)


def test_adopt_platform_field_rejects_unsafe_results(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    other = add_merchant(db_session, name="其他商家")
    service = PlatformAuditService(db_session)
    run = service.create_run(merchant.id)
    conflict = service.record_platform(
        run.id,
        "amap",
        "高德地图",
        found=True,
        fields={"name": "另一家机构", "phone": "0879-1"},
        evidence=[{"url": "https://example.com/conflict"}],
    )
    no_source = service.record_platform(
        run.id,
        "tencent_maps",
        "腾讯地图",
        found=True,
        fields={"name": merchant.name, "phone": "0879-2"},
        evidence=[],
    )
    run.status = "completed"
    db_session.commit()

    with pytest.raises(PlatformAuditAdoptionConflict):
        service.adopt_field(merchant.id, conflict.id, "phone")
    with pytest.raises(PlatformAuditAdoptionInvalid, match="公开来源"):
        service.adopt_field(merchant.id, no_source.id, "phone")
    with pytest.raises(PlatformAuditAdoptionInvalid, match="不支持"):
        service.adopt_field(merchant.id, no_source.id, "unknown")
    with pytest.raises(PlatformAuditResultNotFound):
        service.adopt_field(other.id, no_source.id, "phone")

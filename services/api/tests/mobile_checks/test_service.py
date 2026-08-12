from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.merchants.models import Merchant
from app.mobile_checks.models import MobileCheckResult, MobileCheckRound, MobileRoundSource
from app.mobile_checks.service import MobileCheckService, NoApprovedQueriesError
from app.queries.models import Query, QuerySet


def add_merchant(session: Session) -> Merchant:
    merchant = Merchant(
        name="澜沧舒适口腔",
        normalized_name="澜沧舒适口腔",
        city="普洱市",
        district="澜沧拉祜族自治县",
        industry="口腔医疗",
    )
    session.add(merchant)
    session.flush()
    return merchant


def add_queries(session: Session, merchant: Merchant, count: int) -> QuerySet:
    query_set = QuerySet(merchant_id=merchant.id, version=1, generator_name="test")
    session.add(query_set)
    session.flush()
    categories = ["geo", "category", "product", "price", "occasion", "need"]
    for index in range(count):
        session.add(
            Query(
                query_set_id=query_set.id,
                text=f"验证问题 {index + 1}",
                category=categories[index % len(categories)],
                reason="手机抽样验证",
                priority=(index % 5) + 1,
                intent_type="verification" if index % 4 == 3 else "recommendation",
                review_status="approved" if index != count - 1 else "pending",
                is_enabled=index != count - 2,
            )
        )
    session.commit()
    return query_set


def test_create_validation_set_uses_only_approved_enabled_queries_and_stays_fixed(
    db_session: Session,
) -> None:
    merchant = add_merchant(db_session)
    add_queries(db_session, merchant, 20)

    created = MobileCheckService(db_session).create_validation_set(merchant.id)
    repeated = MobileCheckService(db_session).get_validation_set(created.id, merchant.id)

    assert len(created.items) == 3
    assert {item.query.review_status for item in created.items} == {"approved"}
    assert {item.query.is_enabled for item in created.items} == {True}
    assert {item.query.intent_type for item in created.items} == {"recommendation"}
    assert [item.query_id for item in repeated.items] == [
        item.query_id for item in created.items
    ]
    assert len({item.query.category for item in created.items}) == 3


def test_create_validation_set_rejects_when_latest_set_has_fewer_than_three_recommendations(
    db_session: Session,
) -> None:
    merchant = add_merchant(db_session)
    query_set = QuerySet(merchant_id=merchant.id, version=1, generator_name="test")
    db_session.add(query_set)
    db_session.flush()
    for index in range(2):
        db_session.add(Query(query_set_id=query_set.id, text=f"recommend {index}", category="geo", reason="test", priority=1, intent_type="recommendation", review_status="approved", is_enabled=True))
    db_session.commit()

    with pytest.raises(NoApprovedQueriesError):
        MobileCheckService(db_session).create_validation_set(merchant.id)


def test_create_validation_set_uses_only_newest_query_set(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    old_set = add_queries(db_session, merchant, 10)
    newest = QuerySet(merchant_id=merchant.id, version=2, generator_name="test")
    db_session.add(newest)
    db_session.flush()
    for index, category in enumerate(("geo", "category", "occasion")):
        db_session.add(Query(query_set_id=newest.id, text=f"new {index}", category=category, reason="newest", priority=1, intent_type="recommendation", review_status="approved", is_enabled=True))
    db_session.commit()

    created = MobileCheckService(db_session).create_validation_set(merchant.id)

    assert {item.query.query_set_id for item in created.items} == {newest.id}
    assert old_set.id not in {item.query.query_set_id for item in created.items}


def test_create_validation_set_rejects_merchant_without_approved_queries(
    db_session: Session,
) -> None:
    merchant = add_merchant(db_session)
    session_query_set = QuerySet(merchant_id=merchant.id, version=1, generator_name="test")
    db_session.add(session_query_set)
    db_session.flush()
    db_session.add(
        Query(
            query_set_id=session_query_set.id,
            text="待审核问题",
            category="geo",
            reason="尚未审核",
            priority=1,
            review_status="pending",
            is_enabled=True,
        )
    )
    db_session.commit()

    with pytest.raises(NoApprovedQueriesError):
        MobileCheckService(db_session).create_validation_set(merchant.id)


def test_validation_set_cannot_be_read_through_another_merchant(
    db_session: Session,
) -> None:
    merchant = add_merchant(db_session)
    add_queries(db_session, merchant, 10)
    other = Merchant(
        id=uuid4(),
        name="其他门诊",
        normalized_name="其他门诊",
        city="普洱市",
        industry="口腔医疗",
    )
    db_session.add(other)
    db_session.commit()
    created = MobileCheckService(db_session).create_validation_set(merchant.id)

    assert MobileCheckService(db_session).get_validation_set(created.id, other.id) is None


def test_workspace_metrics_use_only_confirmed_question_results(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    add_queries(db_session, merchant, 6)
    validation_set = MobileCheckService(db_session).create_validation_set(merchant.id)
    round_record = MobileCheckRound(
        merchant_id=merchant.id,
        validation_set_id=validation_set.id,
        status="confirmed",
        location_text="澜沧县",
    )
    db_session.add(round_record)
    db_session.flush()
    levels = ["primary", "supplementary", "none", "primary"]
    for index, item in enumerate(validation_set.items):
        db_session.add(MobileCheckResult(
            round_id=round_record.id,
            validation_item_id=item.id,
            mention_level=levels[index],
            competitors=["王天佑口腔"] if index == 2 else [],
            information_accurate=index != 1,
            is_confirmed=index < 3,
        ))
    db_session.commit()

    workspace = MobileCheckService(db_session).get_workspace(merchant.id)

    assert workspace["metrics"] == {
        "confirmedCount": 3,
        "mentionRate": pytest.approx(2 / 3),
        "primaryRate": pytest.approx(1 / 3),
        "categoryCoverageRate": pytest.approx(2 / 3),
        "informationAccuracyRate": pytest.approx(1 / 2),
        "sourceCoverageRate": 0.0,
    }


def test_source_gap_matrix_uses_confirmed_mobile_sources_and_marks_target_gap(
    db_session: Session,
) -> None:
    merchant = add_merchant(db_session)
    add_queries(db_session, merchant, 6)
    validation_set = MobileCheckService(db_session).create_validation_set(merchant.id)
    round_record = MobileCheckRound(merchant_id=merchant.id, validation_set_id=validation_set.id, status="confirmed")
    db_session.add(round_record)
    db_session.flush()
    db_session.add(MobileCheckResult(round_id=round_record.id, validation_item_id=validation_set.items[0].id, mention_level="none", competitors=["王天佑口腔", "无来源竞品"], is_confirmed=True))
    db_session.add_all([
        MobileRoundSource(round_id=round_record.id, title="舒适口腔工商页", source_type="registry", entity_name=merchant.name, facts=["地址"], evidence_kind="official", access_status="correctable", is_confirmed=True),
        MobileRoundSource(round_id=round_record.id, title="王天佑招聘页", url="https://jobs.example/wty", domain="jobs.example", source_type="recruitment", entity_name="王天佑口腔", facts=["CT", "独立诊室"], evidence_kind="self_reported", access_status="maintainable", is_confirmed=True),
        MobileRoundSource(round_id=round_record.id, title="未确认竞品页", source_type="douyin", entity_name="光雅口腔", facts=["口扫"], evidence_kind="self_reported", access_status="unknown", is_confirmed=False),
    ])
    db_session.commit()

    workspace = MobileCheckService(db_session).get_workspace(merchant.id)
    recruitment = next(row for row in workspace["sourceGaps"] if row["key"] == "recruitment")

    assert workspace["entities"] == [merchant.name, "无来源竞品", "王天佑口腔"]
    assert recruitment["highlight"] is True
    assert recruitment["cells"][merchant.name]["status"] == "missing"
    assert recruitment["cells"]["王天佑口腔"] == {
        "status": "present",
        "evidence": ["王天佑招聘页：CT、独立诊室"],
    }
    equipment = next(row for row in workspace["sourceGaps"] if row["key"] == "equipment")
    assert equipment["cells"]["王天佑口腔"]["evidence"] == ["王天佑招聘页：CT、独立诊室"]


def test_inherited_sources_keep_original_round_provenance(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    add_queries(db_session, merchant, 6)
    validation_set = MobileCheckService(db_session).create_validation_set(merchant.id)
    original = MobileCheckRound(merchant_id=merchant.id, validation_set_id=validation_set.id, status="confirmed")
    db_session.add(original)
    db_session.flush()
    db_session.add(MobileRoundSource(round_id=original.id, title="机构介绍", source_type="profile", entity_name=merchant.name, facts=["营业时间"], evidence_kind="self_reported", access_status="maintainable", is_confirmed=True))
    db_session.flush()
    inherited = MobileCheckRound(merchant_id=merchant.id, validation_set_id=validation_set.id, status="confirmed", inherited_source_round_id=original.id)
    db_session.add(inherited)
    db_session.commit()

    workspace = MobileCheckService(db_session).get_workspace(merchant.id)

    assert workspace["sourceRoundId"] == str(original.id)
    assert workspace["latestRoundId"] == str(inherited.id)

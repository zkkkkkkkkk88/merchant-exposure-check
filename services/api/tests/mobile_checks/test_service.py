from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.merchants.models import Merchant
from app.mobile_checks.models import MobileCheckResult, MobileCheckRound, MobileRoundSource
from app.mobile_checks.schemas import MobileResultCreate, MobileRoundCreate
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


def test_create_validation_set_accepts_exactly_three_selected_recommendations(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    add_queries(db_session, merchant, 10)
    eligible = MobileCheckService(db_session)._approved_queries(merchant.id)[:3]

    created = MobileCheckService(db_session).create_validation_set(
        merchant.id,
        [query.id for query in eligible],
    )

    assert [item.query_id for item in created.items] == [query.id for query in eligible]


def test_create_validation_set_rejects_invalid_selected_questions(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    add_queries(db_session, merchant, 10)
    eligible = MobileCheckService(db_session)._approved_queries(merchant.id)

    with pytest.raises(NoApprovedQueriesError, match="exactly three"):
        MobileCheckService(db_session).create_validation_set(merchant.id, [eligible[0].id])

    with pytest.raises(NoApprovedQueriesError, match="eligible recommendation"):
        MobileCheckService(db_session).create_validation_set(
            merchant.id,
            [eligible[0].id, eligible[1].id, uuid4()],
        )


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
            answer_excerpt=f"豆包完整回答 {index + 1}",
        ))
    db_session.commit()

    workspace = MobileCheckService(db_session).get_workspace(merchant.id)

    assert workspace["metrics"] == {
        "confirmedCount": 3,
        "mentionCount": 2,
        "primaryCount": 1,
        "categoryCoveredCount": 2,
        "categoryTotalCount": 3,
        "informationAccurateCount": 1,
        "informationEvaluatedCount": 2,
        "mentionRate": pytest.approx(2 / 3),
        "primaryRate": pytest.approx(1 / 3),
        "categoryCoverageRate": pytest.approx(2 / 3),
        "informationAccuracyRate": pytest.approx(1 / 2),
        "sourceCoverageRate": 0.0,
    }
    assert workspace["latestRoundAnswers"] == [
        {
            "position": item.position,
            "question": item.query.text,
            "answer": f"豆包完整回答 {item.position}",
            "mentionLevel": levels[item.position - 1],
            "mentionLabel": "首批推荐" if item.position == 1 else "补充提及" if item.position == 2 else "未提及",
            "targetPosition": None,
        }
        for item in validation_set.items[:3]
    ]


def test_create_round_recomputes_mentions_from_full_numbered_answers(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    merchant.name = "澜沧皓雅口腔门诊有限公司"
    add_queries(db_session, merchant, 6)
    validation_set = MobileCheckService(db_session).create_validation_set(merchant.id)
    answers = [
        "\n".join(["说明" * 260, "1. 甲口腔", "2. 乙口腔", "3. 丙口腔", "4. 丁口腔", "5. 戊口腔", "6. 皓雅口腔门诊"]),
        "\n".join(["1. 甲口腔", "2. 乙口腔", "3. 丙口腔", "4. 普洱皓雅口腔门诊有限公司（皓雅口腔）"]),
        "\n".join(["1. 甲口腔", "2. 乙口腔", "3. 皓雅口腔门诊"]),
    ]
    payload = MobileRoundCreate(
        validation_set_id=validation_set.id,
        raw_qa_text="\n\n".join(f"Q{index + 1}：{answer}" for index, answer in enumerate(answers)),
        results=[
            MobileResultCreate(
                validation_item_id=item.id,
                mention_level="none",
                is_confirmed=True,
                answer_excerpt=answer[:500],
            )
            for item, answer in zip(validation_set.items, answers, strict=True)
        ],
    )

    created = MobileCheckService(db_session).create_round(merchant.id, payload)
    assert created is not None
    MobileCheckService(db_session).confirm_round(created.id, merchant.id)
    workspace = MobileCheckService(db_session).get_workspace(merchant.id)

    assert [result.answer_excerpt for result in created.results] == answers
    assert [result.mention_level for result in created.results] == ["supplementary"] * 3
    assert workspace["metrics"]["mentionCount"] == 3
    assert workspace["metrics"]["mentionRate"] == 1.0
    assert [answer["targetPosition"] for answer in workspace["latestRoundAnswers"]] == [6, 4, 3]
    assert [answer["mentionLabel"] for answer in workspace["latestRoundAnswers"]] == ["补充提及"] * 3


def test_mobile_result_accepts_a_complete_long_answer() -> None:
    result = MobileResultCreate(
        validation_item_id=uuid4(),
        mention_level="none",
        answer_excerpt="完整回答" * 1000,
    )

    assert len(result.answer_excerpt or "") == 4000


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
        MobileRoundSource(round_id=round_record.id, title="地图门店", url="https://m.map.360.cn/store/1", domain="m.map.360.cn", source_type="profile", entity_name=merchant.name, facts=["地址"], evidence_kind="third_party", access_status="correctable", is_confirmed=True),
        MobileRoundSource(round_id=round_record.id, title="地图介绍", url="https://m.map.360.cn/store/2", domain="m.map.360.cn", source_type="profile", entity_name=merchant.name, facts=["项目"], evidence_kind="third_party", access_status="reference", is_confirmed=True),
        MobileRoundSource(round_id=round_record.id, title="王天佑招聘页", url="https://jobs.example/wty", domain="jobs.example", source_type="recruitment", entity_name="王天佑口腔", facts=["CT", "独立诊室"], evidence_kind="self_reported", access_status="maintainable", is_confirmed=True),
        MobileRoundSource(round_id=round_record.id, title="未确认竞品页", source_type="douyin", entity_name="光雅口腔", facts=["口扫"], evidence_kind="self_reported", access_status="unknown", is_confirmed=False),
    ])
    db_session.commit()

    workspace = MobileCheckService(db_session).get_workspace(merchant.id)
    recruitment = next(row for row in workspace["sourceGaps"] if row["key"] == "recruitment")

    assert workspace["entities"] == [merchant.name, "王天佑口腔"]
    assert recruitment["highlight"] is True
    assert recruitment["cells"][merchant.name]["status"] == "missing"
    assert recruitment["cells"]["王天佑口腔"] == {
        "status": "present",
        "evidence": ["王天佑招聘页：CT、独立诊室"],
    }
    equipment = next(row for row in workspace["sourceGaps"] if row["key"] == "equipment")
    assert equipment["cells"]["王天佑口腔"]["evidence"] == ["王天佑招聘页：CT、独立诊室"]
    assert workspace["channelMaintenance"]["citedChannels"][0] == {
        "domain": "m.map.360.cn",
        "citationCount": 2,
        "access": "correctable",
        "accessLabel": "需要认领或纠错",
        "sourceTypes": ["机构或门店主页"],
        "links": [
            {"title": "地图门店", "url": "https://m.map.360.cn/store/1"},
            {"title": "地图介绍", "url": "https://m.map.360.cn/store/2"},
        ],
    }
    assert workspace["channelMaintenance"]["candidateChannels"][0] == {
        "channel": "微信公众号文章或机构官网介绍页",
        "content": "完整发布医生、资质、消毒、就诊流程和经营信息，并附可核验材料",
    }


def test_workspace_without_a_round_has_empty_channel_maintenance(
    db_session: Session,
) -> None:
    merchant = add_merchant(db_session)

    workspace = MobileCheckService(db_session).get_workspace(merchant.id)

    assert workspace["channelMaintenance"] == {
        "citedChannels": [],
        "candidateChannels": [],
    }


def test_source_gap_stays_empty_until_sources_are_provided(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    add_queries(db_session, merchant, 6)
    validation_set = MobileCheckService(db_session).create_validation_set(merchant.id)
    round_record = MobileCheckRound(
        merchant_id=merchant.id,
        validation_set_id=validation_set.id,
        status="confirmed",
    )
    db_session.add(round_record)
    db_session.flush()
    db_session.add(MobileCheckResult(
        round_id=round_record.id,
        validation_item_id=validation_set.items[0].id,
        mention_level="none",
        competitors=[f"competitor {index}" for index in range(20)],
        is_confirmed=True,
    ))
    db_session.commit()

    workspace = MobileCheckService(db_session).get_workspace(merchant.id)

    assert workspace["entities"] == [merchant.name]
    assert workspace["sourceGaps"] == []


def test_oral_round_excludes_public_hospital_competitors(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    add_queries(db_session, merchant, 6)
    validation_set = MobileCheckService(db_session).create_validation_set(merchant.id)
    payload = MobileRoundCreate(
        validation_set_id=validation_set.id,
        results=[MobileResultCreate(
            validation_item_id=validation_set.items[0].id,
            mention_level="none",
            competitors=["澜沧县第一人民医院口腔科", "王天佑口腔诊所"],
            is_confirmed=True,
        )],
    )

    created = MobileCheckService(db_session).create_round(merchant.id, payload)

    assert created is not None
    assert created.results[0].competitors == ["王天佑口腔诊所"]


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

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.merchants.models import Merchant
from app.mobile_checks.models import MobileCheckResult, MobileCheckRound
from app.mobile_checks.service import MobileCheckService
from app.mobile_checks.playbook import _concise_reason
from app.queries.models import Query, QuerySet


def seed_mobile_case(db_session: Session) -> tuple[Merchant, MobileCheckRound]:
    merchant = Merchant(
        name="澜沧皓雅口腔门诊部",
        normalized_name="澜沧皓雅口腔门诊部",
        city="普洱市",
        district="澜沧拉祜族自治县",
        industry="口腔医疗",
    )
    db_session.add(merchant)
    db_session.flush()
    query_set = QuerySet(merchant_id=merchant.id, version=1, generator_name="test")
    db_session.add(query_set)
    db_session.flush()
    questions = [
        "澜沧县有什么值得去的口腔医疗机构？",
        "澜沧县有什么口碑好的口腔医疗机构？",
        "澜沧县有什么评价稳定的口腔医疗机构？",
    ]
    queries = []
    for index, text in enumerate(questions):
        query = Query(
            query_set_id=query_set.id,
            text=text,
            category="geo",
            reason="手机验证",
            priority=index + 1,
            intent_type="recommendation",
            review_status="approved",
            is_enabled=True,
        )
        db_session.add(query)
        queries.append(query)
    db_session.commit()
    validation_set = MobileCheckService(db_session).create_validation_set(merchant.id)
    round_record = MobileCheckRound(
        merchant_id=merchant.id,
        validation_set_id=validation_set.id,
        status="confirmed",
        created_at=datetime.now(UTC),
    )
    db_session.add(round_record)
    db_session.flush()
    answers = [
        """1. 澜沧县第一人民医院口腔科：公立医院科室，诊疗项目较齐全。\n2. 王天佑口腔诊所：经营多年，可使用医保。\n3. 澜沧县中医医院口腔科：公立医院科室。\n4. 杨雪梅（光雅）口腔诊所：设有口扫设备。\n5. 皓雅口腔门诊：本地口腔门诊。""",
        "1. 澜沧县第一人民医院口腔科：公立医院。\n2. 王天佑口腔诊所：经营多年。",
        "1. 澜沧县第一人民医院口腔科：评价较稳定。\n2. 澜沧县中医医院口腔科：公立医院。",
    ]
    competitors = [
        ["澜沧县第一人民医院口腔科", "王天佑口腔诊所", "澜沧县中医医院口腔科", "杨雪梅（光雅）口腔诊所"],
        ["澜沧县第一人民医院口腔科", "王天佑口腔诊所"],
        ["澜沧县第一人民医院口腔科", "澜沧县中医医院口腔科"],
    ]
    levels = ["supplementary", "none", "none"]
    for item, answer, names, level in zip(validation_set.items, answers, competitors, levels, strict=True):
        db_session.add(MobileCheckResult(
            round_id=round_record.id,
            validation_item_id=item.id,
            mention_level=level,
            competitors=names,
            answer_excerpt=answer,
            information_accurate=True if level != "none" else None,
            is_confirmed=True,
        ))
    db_session.commit()
    return merchant, round_record


def test_playbook_explains_real_result_with_answer_evidence(db_session: Session) -> None:
    merchant, _ = seed_mobile_case(db_session)

    playbook = MobileCheckService(db_session).get_workspace(merchant.id)["recommendationPlaybook"]

    assert playbook["diagnosis"]["mentionedCount"] == 1
    assert playbook["diagnosis"]["totalCount"] == 3
    assert playbook["diagnosis"]["questions"][0]["targetPosition"] == 5
    assert playbook["diagnosis"]["questions"][1]["mentionLevel"] == "none"
    assert len(playbook["competitorReasons"]) <= 3
    names = [item["name"] for item in playbook["competitorReasons"]]
    assert "王天佑口腔诊所" in names
    assert "杨雪梅（光雅）口腔诊所" not in names
    assert "澜沧县第一人民医院口腔科" not in names
    assert "澜沧县中医医院口腔科" not in names


def test_playbook_only_shows_private_clinics_repeated_across_answers(db_session: Session) -> None:
    merchant, round_record = seed_mobile_case(db_session)
    ordered = sorted(round_record.results, key=lambda item: item.validation_item.position)
    ordered[0].answer_excerpt = """1. 王天佑口腔诊所
地址：勐朗镇
经营时间久，医保定点机构，配备口腔CT；适合基础治疗及种植需求。
2. 杨雪梅口腔（光雅口腔）
主治医师出身公立背景，设备含CBCT、口扫仪，就诊环境新。"""
    ordered[0].competitors = ["上允金钟口腔诊所"]  # intentionally stale parsed data
    ordered[1].answer_excerpt = """1. 王天佑口腔诊所：经营多年，服务项目较全。
2. 福康口腔诊所：营业稳定。上允金钟口腔诊所：上允镇经营。"""
    ordered[1].competitors = ["上允金钟口腔诊所"]
    ordered[2].answer_excerpt = """1. 杨雪梅（光雅）口腔诊所：设备较全，消毒流程规范。
2. 德玉口腔诊所：本地老牌牙科。"""
    ordered[2].competitors = ["上允金钟口腔诊所"]
    db_session.commit()

    competitors = MobileCheckService(db_session).get_workspace(merchant.id)["recommendationPlaybook"]["competitorReasons"]

    assert [item["name"] for item in competitors] == ["王天佑口腔诊所", "杨雪梅口腔（光雅口腔）"]
    assert all(item["questionCount"] == 2 for item in competitors)
    assert "经营时间久" in str(competitors[0]["reasons"])
    assert "设备含CBCT" in str(competitors[1]["reasons"])
    assert "上允金钟口腔诊所" not in str(competitors)


def test_playbook_merges_parenthetical_aliases_and_excludes_target(db_session: Session) -> None:
    merchant, round_record = seed_mobile_case(db_session)
    ordered = sorted(round_record.results, key=lambda item: item.validation_item.position)
    answers = [
        "1. 澜沧王天佑口腔诊所（县城老牌，医保定点）：经营时间较长。\n2. 澜沧皓雅口腔门诊部：目标商家。",
        "1. 澜沧王天佑口腔诊所（医保定点）：服务项目较全。\n2. 皓雅口腔门诊：目标商家。",
        "1. 澜沧皓雅口腔门诊部：目标商家。\n2. 澜沧王天佑口腔（总店+华庭分店）：门店规模较大。",
    ]
    for result, answer in zip(ordered, answers, strict=True):
        result.answer_excerpt = answer
    db_session.commit()

    competitors = MobileCheckService(db_session).get_workspace(merchant.id)["recommendationPlaybook"]["competitorReasons"]

    assert len(competitors) == 1
    assert competitors[0]["name"] == "澜沧王天佑口腔诊所（县城老牌，医保定点）"
    assert competitors[0]["questionCount"] == 3
    assert "皓雅" not in str(competitors)


def test_competitor_reason_stops_before_the_next_clinic() -> None:
    reason = _concise_reason("营业时间稳定，适合基础项目。乡镇-上允金钟口腔诊所：上允镇经营。")

    assert reason == "营业时间稳定，适合基础项目"


def test_playbook_actions_do_not_turn_competitor_claims_into_target_facts(db_session: Session) -> None:
    merchant, _ = seed_mobile_case(db_session)

    actions = MobileCheckService(db_session).get_workspace(merchant.id)["recommendationPlaybook"]["actions"]
    rendered = str(actions)

    assert 1 <= len(actions) <= 3
    assert "统一机构正式名称" in actions[0]["title"]
    assert "补齐口碑与稳定经营" in rendered
    assert "本机构支持医保" not in rendered
    assert "本机构配备CT" not in rendered
    assert all(2 <= len(action["steps"]) <= 4 for action in actions)
    assert all(len(action["examples"]) <= 2 for action in actions)
    assert actions[0]["publishTargets"][0] == {
        "priority": 1,
        "channel": "高德地图、百度地图、腾讯地图",
        "content": "统一机构正式名称、常用简称、地址、电话和营业时间",
    }
    assert all(action["publishTargets"] for action in actions)
    assert all("独立来源审计结果" in action["linkEntryHint"] for action in actions)


def test_playbook_compares_only_same_validation_questions(db_session: Session) -> None:
    merchant, latest = seed_mobile_case(db_session)
    previous = MobileCheckRound(
        merchant_id=merchant.id,
        validation_set_id=latest.validation_set_id,
        status="confirmed",
        created_at=latest.created_at - timedelta(days=7),
    )
    db_session.add(previous)
    db_session.flush()
    latest_items = sorted(latest.results, key=lambda item: item.validation_item.position)
    for result in latest_items:
        db_session.add(MobileCheckResult(
            round_id=previous.id,
            validation_item_id=result.validation_item_id,
            mention_level="none",
            competitors=[],
            answer_excerpt="未提及目标机构",
            is_confirmed=True,
        ))
    db_session.commit()

    comparison = MobileCheckService(db_session).get_workspace(merchant.id)["recommendationPlaybook"]["comparison"]

    assert comparison["mentionRateBefore"] == 0
    assert comparison["mentionRateAfter"] == 1 / 3
    assert comparison["questions"][0]["change"] == "improved"

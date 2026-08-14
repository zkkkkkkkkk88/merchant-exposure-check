from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import app
from app.merchants.schemas import (
    MerchantCreate,
    MerchantProfileFactWrite,
    MerchantProfileWrite,
)
from app.merchants.service import MerchantService
from app.mobile_checks.models import MobileCheckRound
from app.mobile_checks.service import MobileCheckService
from app.platform_audits.models import PlatformAuditRun
from app.queries.schemas import QueryUpdate
from app.queries.service import QueryLibraryService
from app.scans.schemas import (
    ManualCitationCreate,
    ManualResultCreate,
    ManualResultsCreate,
)
from app.scans.service import ScanService


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_manual_scan(
    db_session: Session,
    raw_text: str,
    citations: list[ManualCitationCreate] | None = None,
):
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(
            name="O'eat Gastronomy",
            branch_name="杭州万象城店",
            city="杭州",
            industry="餐饮",
        ),
    )
    MerchantService.replace_profile(
        db_session,
        merchant.id,
        MerchantProfileWrite(
            facts=[
                MerchantProfileFactWrite(
                    field_key="location.city",
                    value="杭州",
                    confirmation_status="confirmed",
                ),
                MerchantProfileFactWrite(
                    field_key="category.precise",
                    value="西餐厅",
                    confirmation_status="confirmed",
                ),
            ]
        ),
    )
    query_set = QueryLibraryService.generate(db_session, merchant.id, count=6)
    query = query_set.queries[0]
    QueryLibraryService.update_query(
        db_session,
        query.id,
        QueryUpdate(review_status="approved", is_enabled=True),
    )
    for item in query_set.queries[1:]:
        QueryLibraryService.update_query(
            db_session,
            item.id,
            QueryUpdate(review_status="rejected", is_enabled=False),
        )
    run = ScanService.create_run(db_session, merchant.id, query_set.id, "manual")
    ScanService.add_manual_results(
        db_session,
        run.id,
        ManualResultsCreate(
            results=[
                ManualResultCreate(
                    query_id=query.id,
                    raw_text=raw_text,
                    citations=citations or [],
                )
            ]
        ),
    )
    return merchant, query, run


def test_journey_progress_starts_with_profile_and_never_claims_external_action_done(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="Progress Store", city="Hangzhou", industry="Dining"),
    )

    response = client.get(f"/merchants/{merchant.id}/journey-progress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["completed_count"] == 0
    assert payload["total_count"] == 6
    assert payload["current_step"] == "profile"
    assert [item["status"] for item in payload["steps"]] == [
        "pending",
        "pending",
        "pending",
        "pending",
        "pending",
        "pending",
    ]


def test_journey_progress_marks_internal_evidence_and_keeps_action_as_ready(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="Progress Clinic", city="Lancang", industry="Dental"),
    )
    MerchantService.replace_profile(
        db_session,
        merchant.id,
        MerchantProfileWrite(
            facts=[
                MerchantProfileFactWrite(
                    field_key="identity.official_name",
                    value="Progress Clinic",
                    confirmation_status="confirmed",
                ),
                MerchantProfileFactWrite(
                    field_key="location.city",
                    value="Lancang",
                    confirmation_status="confirmed",
                ),
                MerchantProfileFactWrite(
                    field_key="category.precise",
                    value="Private dental clinic",
                    confirmation_status="confirmed",
                ),
            ]
        ),
    )
    query_set = QueryLibraryService.generate(db_session, merchant.id, count=6)
    recommendation_queries = [
        query for query in query_set.queries if query.intent_type == "recommendation"
    ][:3]
    for query in recommendation_queries:
        QueryLibraryService.update_query(
            db_session,
            query.id,
            QueryUpdate(review_status="approved", is_enabled=True),
        )
    validation_set = MobileCheckService(db_session).create_validation_set(merchant.id)
    db_session.add_all(
        [
            PlatformAuditRun(merchant_id=merchant.id, status="completed"),
            MobileCheckRound(
                merchant_id=merchant.id,
                validation_set_id=validation_set.id,
                status="confirmed",
            ),
        ]
    )
    db_session.commit()

    response = client.get(f"/merchants/{merchant.id}/journey-progress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["completed_count"] == 4
    assert [item["status"] for item in payload["steps"]] == [
        "completed",
        "completed",
        "completed",
        "completed",
        "ready",
        "ready",
    ]
    assert payload["current_step"] == "action"

    db_session.add(
        MobileCheckRound(
            merchant_id=merchant.id,
            validation_set_id=validation_set.id,
            status="confirmed",
        )
    )
    db_session.commit()

    retested = client.get(f"/merchants/{merchant.id}/journey-progress").json()
    assert retested["completed_count"] == 5
    assert retested["steps"][-1]["status"] == "completed"
    assert retested["steps"][-2]["status"] == "ready"


def test_report_calculates_target_mention_and_accepts_manual_check(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant, query, run = create_manual_scan(
        db_session,
        "1. O'eat Gastronomy：适合约会。",
    )

    report = client.get(f"/merchants/{merchant.id}/reports/{run.id}")

    assert report.status_code == 200
    assert float(report.json()["metrics"]["mention_rate"]) == 1.0
    assert report.json()["metrics"]["visibility_stage"] == "recommended"
    assert "first_position_rate" not in report.json()["metrics"]

    dashboard = client.get(f"/merchants/{merchant.id}/dashboard")
    assert dashboard.status_code == 200
    assert float(dashboard.json()["metrics"]["mentionRate"]) == 1.0
    assert dashboard.json()["metrics"]["visibilityStage"] == "recommended"
    assert "firstPositionRate" not in dashboard.json()["metrics"]
    assert dashboard.json()["merchant"]["name"] == "O'eat Gastronomy"

    checked = client.post(
        f"/scan-runs/{run.id}/manual-checks",
        json={
            "query_id": str(query.id),
            "answer_summary": "豆包 App 第一位提及目标商家",
            "mentioned": True,
            "position": 1,
            "sources": ["https://example.com/app-source"],
        },
    )
    assert checked.status_code == 201
    listed = client.get(f"/scan-runs/{run.id}/manual-checks")
    assert listed.status_code == 200
    assert listed.json()[0]["position"] == 1


def test_history_returns_metric_delta(client: TestClient, db_session: Session) -> None:
    merchant, _, first = create_manual_scan(
        db_session,
        "1. O'eat Gastronomy：适合约会。",
    )
    query_set = QueryLibraryService.generate(db_session, merchant.id, count=6)
    query = query_set.queries[0]
    QueryLibraryService.update_query(
        db_session,
        query.id,
        QueryUpdate(review_status="approved", is_enabled=True),
    )
    for item in query_set.queries[1:]:
        QueryLibraryService.update_query(
            db_session,
            item.id,
            QueryUpdate(review_status="rejected", is_enabled=False),
        )
    second = ScanService.create_run(db_session, merchant.id, query_set.id, "manual")
    ScanService.add_manual_results(
        db_session,
        second.id,
        ManualResultsCreate(
            results=[ManualResultCreate(query_id=query.id, raw_text="推荐其他餐厅。")]
        ),
    )

    response = client.get(
        f"/merchants/{merchant.id}/history?left={first.id}&right={second.id}"
    )

    assert response.status_code == 200
    assert float(response.json()["deltas"]["mention_rate"]) == -1.0
    assert "first_position_rate" not in response.json()["deltas"]


def test_dashboard_aggregates_ranked_peers_and_uses_category_denominator(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant, _, _ = create_manual_scan(
        db_session,
        """
        1. O'eat Gastronomy（杭州万象城店）：适合约会。
        2. Alimentari Mulino（杭州万象城店）：手工意面。
        3. pennehut畔尼意面（杭州万象城店）：交通方便。
        """,
        citations=[
            ManualCitationCreate(
                url="https://example.com/alimentari",
                title="Alimentari Mulino 杭州万象城店",
                snippet="杭州万象城西餐厅",
            ),
            ManualCitationCreate(
                url="https://example.com/roundup",
                title="杭州西餐厅推荐",
                snippet="多家餐厅合集",
            ),
        ],
    )

    response = client.get(f"/merchants/{merchant.id}/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["categories"] == [
        {"name": "精准品类", "rate": "1.0000", "mentioned": 1, "total": 1}
    ]
    assert payload["competitors"] == [
        {
            "name": "Alimentari Mulino",
            "mentions": 1,
            "comparisonLevel": "candidate",
            "contexts": ["精准品类"],
            "questions": ["杭州有什么值得去的西餐厅？"],
            "sourceCount": 1,
            "reasons": ["手工意面。"],
        },
        {
            "name": "pennehut畔尼意面",
            "mentions": 1,
            "comparisonLevel": "candidate",
            "contexts": ["精准品类"],
            "questions": ["杭州有什么值得去的西餐厅？"],
            "sourceCount": 0,
            "reasons": ["交通方便。"],
        },
    ]


def test_dashboard_creates_cautious_action_for_an_uncovered_category(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant, _, run = create_manual_scan(
        db_session,
        "1. Alimentari Mulino（杭州万象城店）：适合约会。",
        citations=[ManualCitationCreate(url="https://m.39.net/oral/article", title="口腔资讯")],
    )

    response = client.get(f"/merchants/{merchant.id}/dashboard")

    assert response.status_code == 200
    action = response.json()["actions"][0]
    assert action["id"] == "coverage-category"
    assert action["title"] == "核对并统一精准品类信息的公开表述"
    assert action["priority"] == "medium"
    assert action["evidenceCount"] == 1
    assert action["description"]
    assert len(action["steps"]) >= 3
    assert "官网" in action["channels"]
    assert action["materials"]
    assert action["example"]
    assert action["completionCriteria"]
    assert action["questions"] == ["杭州有什么值得去的西餐厅？"]
    assert action["sourceChannels"] == [
        {"domain": "m.39.net", "citationCount": 1, "access": "reference", "label": "仅作参照"}
    ]

    report = client.get(f"/merchants/{merchant.id}/reports/{run.id}")
    assert report.status_code == 200
    assert report.json()["findings"] == [
        {
            "title": "核对并统一精准品类信息的公开表述",
            "description": "本次1道精准品类问题中均未识别到目标商家；请先核对公开页面中的品类表述和城市关联。",
            "priority": "medium",
            "certainty": "confirmed",
            "evidenceCount": 1,
            "questions": ["杭州有什么值得去的西餐厅？"],
        }
    ]


def test_unrelated_answer_citations_do_not_count_as_target_sources(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant, _, run = create_manual_scan(
        db_session,
        "1. O'eat Gastronomy：适合约会。",
        citations=[
            ManualCitationCreate(
                url="https://example.com/unrelated",
                title="杭州西餐厅综合推荐",
                snippet="其他餐厅信息",
            )
        ],
    )

    response = client.get(f"/merchants/{merchant.id}/reports/{run.id}")

    assert response.status_code == 200
    assert response.json()["metrics"]["source_coverage_rate"] == "0.0000"


def test_dashboard_trend_uses_only_runs_from_the_same_query_set(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant, query, first = create_manual_scan(
        db_session,
        "1. O'eat Gastronomy：适合约会。",
    )
    second = ScanService.create_run(
        db_session,
        merchant.id,
        first.query_set_id,
        "manual",
    )
    ScanService.add_manual_results(
        db_session,
        second.id,
        ManualResultsCreate(
            results=[
                ManualResultCreate(
                    query_id=query.id,
                    raw_text="1. Alimentari Mulino：适合约会。",
                )
            ]
        ),
    )

    response = client.get(f"/merchants/{merchant.id}/dashboard")

    assert response.status_code == 200
    assert [point["target"] for point in response.json()["trend"]] == [
        "0.3125",
        "0.0625",
    ]
    assert all("benchmark" not in point for point in response.json()["trend"])

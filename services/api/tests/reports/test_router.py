from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import app
from app.merchants.schemas import MerchantCreate
from app.merchants.service import MerchantService
from app.queries.schemas import QueryUpdate
from app.queries.service import QueryLibraryService
from app.scans.schemas import ManualResultCreate, ManualResultsCreate
from app.scans.service import ScanService


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_manual_scan(db_session: Session, raw_text: str):
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(
            name="O'eat Gastronomy",
            branch_name="杭州万象城店",
            city="杭州",
            industry="餐饮",
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
            results=[ManualResultCreate(query_id=query.id, raw_text=raw_text)]
        ),
    )
    return merchant, query, run


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
    assert float(report.json()["metrics"]["first_position_rate"]) == 1.0

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

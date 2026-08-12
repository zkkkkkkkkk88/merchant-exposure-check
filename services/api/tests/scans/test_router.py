from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import app
from app.merchants.schemas import MerchantCreate
from app.merchants.service import MerchantService
from app.queries.generator import TemplateQueryGenerator
from app.queries.schemas import QueryUpdate
from app.queries.service import QueryLibraryService


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_approved_query_set(db_session: Session):
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="测试餐厅", city="杭州", industry="餐饮"),
    )
    query_set = QueryLibraryService.generate(
        db_session,
        merchant.id,
        count=6,
        generator=TemplateQueryGenerator(),
    )
    approved = query_set.queries[0]
    QueryLibraryService.update_query(
        db_session,
        approved.id,
        QueryUpdate(review_status="approved", is_enabled=True),
    )
    return merchant, query_set, approved


def test_create_get_and_import_manual_scan_result(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant, query_set, query = create_approved_query_set(db_session)

    created = client.post(
        "/scan-runs",
        json={
            "merchant_id": str(merchant.id),
            "query_set_id": str(query_set.id),
            "adapter_name": "manual",
        },
    )

    assert created.status_code == 201
    scan_id = created.json()["id"]
    imported = client.post(
        f"/scan-runs/{scan_id}/manual-results",
        json={
            "results": [
                {
                    "query_id": str(query.id),
                    "raw_text": "推荐测试餐厅。",
                    "citations": [{"url": "https://example.com/review", "title": "测评"}],
                }
            ]
        },
    )

    assert imported.status_code == 200
    assert imported.json()["status"] == "completed"
    fetched = client.get(f"/scan-runs/{scan_id}")
    assert fetched.status_code == 200
    assert fetched.json()["results"][0]["raw_text"] == "推荐测试餐厅。"


def test_manual_import_rejects_query_from_another_set(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant, query_set, _ = create_approved_query_set(db_session)
    created = client.post(
        "/scan-runs",
        json={
            "merchant_id": str(merchant.id),
            "query_set_id": str(query_set.id),
            "adapter_name": "manual",
        },
    )

    response = client.post(
        f"/scan-runs/{created.json()['id']}/manual-results",
        json={"results": [{"query_id": str(uuid4()), "raw_text": "无效结果"}]},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Manual result query does not belong to scan"}

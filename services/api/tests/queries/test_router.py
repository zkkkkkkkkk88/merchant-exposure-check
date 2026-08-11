from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import app
from app.merchants.schemas import MerchantCreate
from app.merchants.service import MerchantService


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_generate_review_and_list_query_set(client: TestClient, db_session: Session) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="测试餐厅", city="杭州", industry="餐饮"),
    )

    generated = client.post(
        f"/merchants/{merchant.id}/query-sets/generate",
        json={"count": 6},
    )

    assert generated.status_code == 201
    body = generated.json()
    assert body["version"] == 1
    assert len(body["queries"]) == 6

    query_id = body["queries"][0]["id"]
    reviewed = client.patch(
        f"/queries/{query_id}",
        json={"review_status": "approved", "is_enabled": True},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["review_status"] == "approved"

    listed = client.get(f"/merchants/{merchant.id}/query-sets")
    assert listed.status_code == 200
    assert listed.json()[0]["version"] == 1


def test_generate_rejects_unknown_merchant(client: TestClient) -> None:
    response = client.post(
        f"/merchants/{uuid4()}/query-sets/generate",
        json={"count": 6},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Merchant not found"}

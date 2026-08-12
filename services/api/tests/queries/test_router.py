from collections.abc import Iterator
from uuid import uuid4

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

    generated = client.post(
        f"/merchants/{merchant.id}/query-sets/generate",
        json={"count": 6},
    )

    assert generated.status_code == 201
    body = generated.json()
    assert body["version"] == 1
    assert len(body["queries"]) == 6
    assert all(query["intent_type"] in {"recommendation", "verification"} for query in body["queries"])

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


def test_generate_requires_confirmed_city_and_precise_category(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="测试餐厅", city="杭州", industry="餐饮"),
    )

    response = client.post(
        f"/merchants/{merchant.id}/query-sets/generate",
        json={"count": 6},
    )

    assert response.status_code == 409
    assert "confirmed city and precise category" in response.json()["detail"]

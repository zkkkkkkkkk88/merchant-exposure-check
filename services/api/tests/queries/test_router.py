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
from app.mobile_checks.models import MobileValidationItem, MobileValidationSet
from app.queries.models import Query, QuerySet


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


def test_cleanup_deletes_unused_old_set_and_archives_referenced_old_set(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="cleanup merchant", city="city", industry="oral care"),
    )
    sets = []
    for version in (1, 2, 3):
        query_set = QuerySet(merchant_id=merchant.id, version=version, generator_name="test")
        db_session.add(query_set)
        db_session.flush()
        query = Query(query_set_id=query_set.id, text=f"question {version}", category="geo", reason="test", priority=1)
        db_session.add(query)
        db_session.flush()
        sets.append((query_set, query))
    validation = MobileValidationSet(merchant_id=merchant.id)
    db_session.add(validation)
    db_session.flush()
    db_session.add(MobileValidationItem(validation_set_id=validation.id, query_id=sets[0][1].id, position=1))
    db_session.commit()

    response = client.post(f"/merchants/{merchant.id}/query-sets/cleanup")

    assert response.status_code == 200
    assert response.json() == {"deleted": 1, "archived": 1, "kept": 1}
    assert db_session.get(QuerySet, sets[0][0].id).is_archived is True
    assert db_session.get(QuerySet, sets[1][0].id) is None
    assert db_session.get(QuerySet, sets[2][0].id).is_archived is False
    listed = client.get(f"/merchants/{merchant.id}/query-sets").json()
    assert [item["version"] for item in listed] == [3]

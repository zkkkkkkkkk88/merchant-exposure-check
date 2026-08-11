from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import app
from app.merchants.profile import confirmed_fact_map
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


def test_only_confirmed_profile_facts_are_available_to_generators(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(
            name="O'eat Gastronomy",
            city="杭州",
            industry="餐饮",
            price_range="双人餐 300–450 元",
        ),
    )

    response = client.put(
        f"/merchants/{merchant.id}/profile",
        json={
            "facts": [
                {
                    "field_key": "category.precise",
                    "value": "西餐厅",
                    "confirmation_status": "confirmed",
                    "confidence": 0.98,
                    "source_urls": ["https://example.com/oeat"],
                },
                {
                    "field_key": "service.baby_chair",
                    "value": True,
                    "confirmation_status": "pending",
                    "confidence": 0.72,
                    "source_urls": [],
                },
            ]
        },
    )

    assert response.status_code == 200
    profile = response.json()
    assert profile["facts"][0]["source_urls"] == ["https://example.com/oeat"]
    assert confirmed_fact_map(profile["facts"]) == {"category.precise": "西餐厅"}


def test_existing_merchant_columns_are_returned_as_pending_candidates(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(
            name="O'eat Gastronomy",
            city="杭州",
            industry="餐饮",
            district="上城区",
            price_range="双人餐 300–450 元",
            products=["西餐"],
        ),
    )

    response = client.get(f"/merchants/{merchant.id}/profile")

    assert response.status_code == 200
    facts = {item["field_key"]: item for item in response.json()["facts"]}
    assert facts["location.city"]["value"] == "杭州"
    assert facts["location.city"]["confirmation_status"] == "pending"
    assert facts["price.display"]["value"] == "双人餐 300–450 元"
    assert facts["category.legacy"]["value"] == "餐饮"


def test_profile_rejects_duplicate_field_keys(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="测试商家", city="杭州", industry="餐饮"),
    )

    response = client.put(
        f"/merchants/{merchant.id}/profile",
        json={
            "facts": [
                {"field_key": "category.precise", "value": "西餐厅"},
                {"field_key": "category.precise", "value": "牛排馆"},
            ]
        },
    )

    assert response.status_code == 422


def test_profile_parser_extracts_restaurant_facts_as_pending_candidates(
    client: TestClient,
    db_session: Session,
) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="O'eat Gastronomy", city="杭州", industry="餐饮"),
    )

    response = client.post(
        f"/merchants/{merchant.id}/profile/parse",
        json={
            "raw_text": "O'eat Gastronomy 是杭州万象城西餐厅，双人餐在300到450元，提供宝宝椅，无烟餐厅，地铁直达，适合约会和亲子。",
            "source_urls": ["https://example.com/oeat"],
        },
    )

    assert response.status_code == 200
    facts = {item["field_key"]: item for item in response.json()["facts"]}
    assert facts["category.precise"]["value"] == "西餐厅"
    assert facts["price.display"]["value"] == "双人餐 300–450 元"
    assert facts["service.baby_chair"]["value"] is True
    assert facts["service.smoke_free"]["value"] is True
    assert facts["need.transport"]["value"] == "交通方便"
    assert facts["occasion.list"]["value"] == ["约会", "亲子"]
    assert all(item["confirmation_status"] == "pending" for item in facts.values())

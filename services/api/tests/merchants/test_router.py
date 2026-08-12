from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import app


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_and_list_merchants(client: TestClient) -> None:
    response = client.post(
        "/merchants",
        json={
            "name": "O'eat Gastronomy",
            "branch_name": "杭州万象城店",
            "city": "杭州",
            "industry": "餐饮",
            "sources": [
                {
                    "kind": "meituan",
                    "url": "https://pmtmeishi.meituan.com/dp/prefer/list/1510759369",
                }
            ],
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "O'eat Gastronomy"
    assert client.get("/merchants").json()[0]["city"] == "杭州"


def test_unknown_merchant_returns_not_found(client: TestClient) -> None:
    response = client.get(f"/merchants/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Merchant not found"}


def test_invalid_source_scheme_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/merchants",
        json={
            "name": "测试商家",
            "city": "杭州",
            "industry": "餐饮",
            "sources": [{"kind": "other", "url": "ftp://example.com/file"}],
        },
    )

    assert response.status_code == 422

from collections.abc import Iterator

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.access import require_admin
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.main import app


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="sqlite+pysqlite:///:memory:",
        access_auth_required=True,
        internal_api_secret="test-internal-secret",
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        ("post", "/merchants", {"name": "访客商家", "city": "杭州"}),
        ("patch", "/merchants/00000000-0000-0000-0000-000000000001", {"name": "改名"}),
        ("post", "/merchants/00000000-0000-0000-0000-000000000001/query-sets/generate", {}),
        ("post", "/scan-runs", {"merchant_id": "00000000-0000-0000-0000-000000000001", "query_set_id": "00000000-0000-0000-0000-000000000002", "adapter_name": "ark"}),
        ("post", "/merchants/00000000-0000-0000-0000-000000000001/platform-audits", {}),
        ("post", "/merchants/00000000-0000-0000-0000-000000000001/mobile-validation-sets", {}),
    ],
)
def test_demo_cannot_call_business_mutations(
    client: TestClient,
    demo_headers: dict[str, str],
    method: str,
    path: str,
    json: dict[str, str],
) -> None:
    response = getattr(client, method)(path, json=json, headers=demo_headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Demo access is read-only"


def test_demo_can_read_merchants(client: TestClient, demo_headers: dict[str, str]) -> None:
    response = client.get("/merchants", headers=demo_headers)

    assert response.status_code == 200


def _requires_admin(dependant: Dependant) -> bool:
    return dependant.call is require_admin or any(
        _requires_admin(child) for child in dependant.dependencies
    )


def _api_routes() -> list[APIRoute]:
    routes: list[APIRoute] = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append(route)
        elif router := getattr(route, "original_router", None):
            routes.extend(
                child for child in router.routes if isinstance(child, APIRoute)
            )
    return routes


def test_every_business_mutation_requires_admin() -> None:
    mutation_methods = {"POST", "PUT", "PATCH", "DELETE"}
    mutation_routes = [
        route
        for route in _api_routes()
        if route.methods & mutation_methods
    ]

    assert mutation_routes
    assert all(_requires_admin(route.dependant) for route in mutation_routes)

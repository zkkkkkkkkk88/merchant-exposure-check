import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.main import app


def test_health_returns_ok() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_system_status_reports_runtime_and_configured_integrations(
    db_session: Session,
    tmp_path,
) -> None:
    heartbeat = tmp_path / "worker-heartbeat.json"
    heartbeat.write_text(
        json.dumps({"updated_at": datetime.now(UTC).isoformat()}),
        encoding="utf-8",
    )
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="sqlite+pysqlite:///:memory:",
        ark_api_key=SecretStr("ark-test"),
        amap_key=SecretStr("amap-test"),
        tencent_map_key=SecretStr(""),
        runtime_dir=tmp_path,
    )

    try:
        response = TestClient(app).get("/system/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "api": "ok",
        "database": "ok",
        "worker": "ok",
        "integrations": {
            "doubao": True,
            "amap": True,
            "tencent_map": False,
        },
    }


def test_system_status_is_degraded_when_worker_has_no_heartbeat(
    db_session: Session,
    tmp_path,
) -> None:
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="sqlite+pysqlite:///:memory:",
        runtime_dir=tmp_path,
    )

    try:
        response = TestClient(app).get("/system/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["worker"] == "offline"


def test_local_frontend_can_preflight_merchant_creation() -> None:
    response = TestClient(app).options(
        "/merchants",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert "POST" in response.headers["access-control-allow-methods"]

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import app
from tests.platform_audits.test_service import add_merchant


def test_platform_audit_can_be_created_and_read(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    created = client.post(f"/merchants/{merchant.id}/platform-audits")
    latest = client.get(f"/merchants/{merchant.id}/platform-audits/latest")

    assert created.status_code == 201
    assert created.json()["status"] == "queued"
    assert latest.status_code == 200
    assert latest.json()["id"] == created.json()["id"]
    app.dependency_overrides.clear()

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


def test_platform_field_can_be_adopted_through_the_api(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    from app.platform_audits.service import PlatformAuditService

    service = PlatformAuditService(db_session)
    run = service.create_run(merchant.id)
    result = service.record_platform(
        run.id,
        "amap",
        "高德地图",
        found=True,
        fields={"name": merchant.name, "address": merchant.address, "phone": "0879-7594999"},
        evidence=[{"url": "https://www.amap.com/place/example"}],
    )
    run.status = "completed"
    db_session.commit()
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    response = client.post(
        f"/merchants/{merchant.id}/platform-audits/results/{result.id}/adopt",
        json={"field_key": "phone"},
    )

    assert response.status_code == 200
    assert response.json()["baseline_fields"]["phone"] == "0879-7594999"
    profile = client.get(f"/merchants/{merchant.id}/profile").json()
    phone = next(fact for fact in profile["facts"] if fact["field_key"] == "contact.phone")
    assert phone["value"] == "0879-7594999"
    assert phone["source_urls"] == ["https://www.amap.com/place/example"]
    app.dependency_overrides.clear()

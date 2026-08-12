from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import app
from tests.mobile_checks.test_service import add_merchant, add_queries


def client_for(session: Session) -> TestClient:
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


def test_round_can_be_created_in_one_batch_and_confirmed(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    add_queries(db_session, merchant, 6)
    client = client_for(db_session)
    validation = client.post(f"/merchants/{merchant.id}/mobile-validation-sets")
    assert validation.status_code == 201
    items = validation.json()["items"]

    created = client.post(
        f"/merchants/{merchant.id}/mobile-check-rounds",
        json={
            "validation_set_id": validation.json()["id"],
            "location_text": "澜沧县",
            "web_search_enabled": True,
            "raw_qa_text": "问题一\n回答一\n\n问题二\n回答二",
            "results": [
                {"validation_item_id": items[0]["id"], "mention_level": "primary", "competitors": ["王天佑口腔"], "information_accurate": True, "is_confirmed": True},
                {"validation_item_id": items[1]["id"], "mention_level": "none", "competitors": ["王天佑口腔"], "is_confirmed": True},
            ],
            "sources": [
                {"title": "王天佑招聘页", "url": "https://jobs.example/wty", "source_type": "recruitment", "entity_name": "王天佑口腔", "facts": ["CT"], "evidence_kind": "self_reported", "access_status": "maintainable", "is_confirmed": True}
            ],
        },
    )
    assert created.status_code == 201
    round_id = created.json()["id"]

    confirmed = client.post(f"/merchants/{merchant.id}/mobile-check-rounds/{round_id}/confirm")
    workspace = client.get(f"/merchants/{merchant.id}/mobile-checks/workspace")

    assert confirmed.status_code == 200
    assert workspace.status_code == 200
    assert workspace.json()["metrics"]["confirmedCount"] == 2
    assert workspace.json()["metrics"]["mentionRate"] == 0.5
    app.dependency_overrides.clear()


def test_round_rejects_validation_set_owned_by_another_merchant(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    add_queries(db_session, merchant, 6)
    other = add_merchant(db_session)
    client = client_for(db_session)
    validation = client.post(f"/merchants/{merchant.id}/mobile-validation-sets").json()

    response = client.post(
        f"/merchants/{other.id}/mobile-check-rounds",
        json={"validation_set_id": validation["id"], "raw_qa_text": "x", "results": [], "sources": []},
    )

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_evidence_upload_accepts_images_and_rejects_other_files(db_session: Session, tmp_path, monkeypatch) -> None:
    merchant = add_merchant(db_session)
    add_queries(db_session, merchant, 6)
    client = client_for(db_session)
    validation = client.post(f"/merchants/{merchant.id}/mobile-validation-sets").json()
    round_id = client.post(
        f"/merchants/{merchant.id}/mobile-check-rounds",
        json={"validation_set_id": validation["id"], "raw_qa_text": "问答", "results": [], "sources": []},
    ).json()["id"]
    monkeypatch.setenv("MOBILE_EVIDENCE_DIR", str(tmp_path))

    image = client.post(
        f"/merchants/{merchant.id}/mobile-check-rounds/{round_id}/evidence",
        content=b"jpeg-bytes",
        headers={"content-type": "image/jpeg", "x-filename": "sources.jpg"},
    )
    text = client.post(
        f"/merchants/{merchant.id}/mobile-check-rounds/{round_id}/evidence",
        content=b"not-image",
        headers={"content-type": "text/plain", "x-filename": "notes.txt"},
    )

    assert image.status_code == 201
    assert image.json()["original_name"] == "sources.jpg"
    assert text.status_code == 400
    app.dependency_overrides.clear()

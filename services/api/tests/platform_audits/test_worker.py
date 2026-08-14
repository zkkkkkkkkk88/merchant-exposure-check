import json

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.platform_audits.models import PlatformAuditRun
from app.platform_audits.worker import PLATFORM_CATALOG, process_next_platform_audit
from app.scans.adapters.base import RawCitation, SearchRequest, SearchResponse
from tests.platform_audits.test_service import add_merchant


class PublicInfoAdapter:
    name = "fake"

    async def search(self, request: SearchRequest) -> SearchResponse:
        return SearchResponse(
            raw_text=json.dumps(
                {
                    "found": True,
                    "fields": {
                        "name": "澜沧皓雅口腔门诊部",
                        "address": "云南省普洱市澜沧县",
                        "products": ["种植牙"],
                    },
                },
                ensure_ascii=False,
            ),
            citations=[RawCitation(url="https://example.com/public", title="公开页面")],
        )


@pytest.mark.asyncio
async def test_worker_audits_each_public_platform_and_finishes(db_session: Session) -> None:
    merchant = add_merchant(db_session)
    from app.platform_audits.service import PlatformAuditService

    run = PlatformAuditService(db_session).create_run(merchant.id)
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)

    processed = await process_next_platform_audit(factory, PublicInfoAdapter())

    db_session.expire_all()
    completed = db_session.get(PlatformAuditRun, run.id)
    assert processed == run.id
    assert completed is not None and completed.status == "completed"
    assert len(completed.platforms) == len(PLATFORM_CATALOG)
    assert completed.platforms[0].evidence[0]["url"] == "https://example.com/public"

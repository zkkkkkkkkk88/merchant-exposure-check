import subprocess
import sys
from collections.abc import Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.merchants.schemas import MerchantCreate
from app.merchants.service import MerchantService
from app.queries.schemas import QueryUpdate
from app.queries.service import QueryLibraryService
from app.scans.adapters.base import (
    RawCitation,
    RetryableAdapterError,
    SearchRequest,
    SearchResponse,
)
from app.scans.models import QueryResult, ScanRun
from app.scans.service import ScanService
from app.scans.worker import build_adapter_registry, process_next_scan


def test_standalone_worker_registers_all_foreign_key_tables() -> None:
    script = (
        "from app.scans import worker; "
        "from app.db.base import Base; "
        "print('merchants' in Base.metadata.tables)"
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=True,
        text=True,
    )

    assert completed.stdout.strip() == "True"


class SequenceAdapter:
    name = "sequence"

    def __init__(self, outcomes: Iterator[SearchResponse | Exception]) -> None:
        self._outcomes = outcomes

    async def search(self, request: SearchRequest) -> SearchResponse:
        outcome = next(self._outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_worker_registry_only_enables_ark_with_server_key() -> None:
    assert build_adapter_registry(Settings(ark_api_key="")) == {}
    registry = build_adapter_registry(Settings(ark_api_key="server-key", ark_model="model"))
    assert set(registry) == {"ark"}


def create_approved_scan(db_session: Session, query_count: int) -> ScanRun:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="测试餐厅", city="杭州", industry="餐饮"),
    )
    query_set = QueryLibraryService.generate(db_session, merchant.id, count=6)
    for query in query_set.queries[:query_count]:
        QueryLibraryService.update_query(
            db_session,
            query.id,
            QueryUpdate(review_status="approved", is_enabled=True),
        )
    for query in query_set.queries[query_count:]:
        QueryLibraryService.update_query(
            db_session,
            query.id,
            QueryUpdate(review_status="rejected", is_enabled=False),
        )
    return ScanService.create_run(db_session, merchant.id, query_set.id, "sequence")


@pytest.mark.asyncio
async def test_worker_completes_scan_and_keeps_raw_evidence(db_session: Session) -> None:
    run = create_approved_scan(db_session, query_count=1)
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    adapter = SequenceAdapter(
        iter(
            [
                SearchResponse(
                    raw_text="推荐测试餐厅。",
                    citations=[RawCitation(url="https://example.com/review", title="测评")],
                    provider_request_id="provider-1",
                )
            ]
        )
    )

    processed_id = await process_next_scan(factory, {"sequence": adapter}, retry_delays=(0,))

    db_session.expire_all()
    completed = db_session.get(ScanRun, run.id)
    result = db_session.scalar(select(QueryResult).where(QueryResult.scan_run_id == run.id))
    assert processed_id == run.id
    assert completed is not None and completed.status == "completed"
    assert result is not None and result.raw_text == "推荐测试餐厅。"
    assert result.provider_request_id == "provider-1"
    assert result.citations[0].url == "https://example.com/review"


@pytest.mark.asyncio
async def test_worker_marks_scan_partial_when_some_queries_fail(db_session: Session) -> None:
    run = create_approved_scan(db_session, query_count=2)
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    adapter = SequenceAdapter(
        iter([SearchResponse(raw_text="成功", citations=[]), ValueError("invalid response")])
    )

    await process_next_scan(factory, {"sequence": adapter}, retry_delays=(0,))

    db_session.expire_all()
    partial = db_session.get(ScanRun, run.id)
    assert partial is not None and partial.status == "partial"
    assert partial.success_count == 1
    assert partial.failure_count == 1


@pytest.mark.asyncio
async def test_worker_stops_after_two_retryable_failures(db_session: Session) -> None:
    run = create_approved_scan(db_session, query_count=1)
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    adapter = SequenceAdapter(
        iter([RetryableAdapterError("rate limited"), RetryableAdapterError("rate limited")])
    )

    await process_next_scan(factory, {"sequence": adapter}, retry_delays=(0,))

    db_session.expire_all()
    failed = db_session.get(ScanRun, run.id)
    result = db_session.scalar(select(QueryResult).where(QueryResult.scan_run_id == run.id))
    assert failed is not None and failed.status == "failed"
    assert result is not None and result.attempt_count == 2
    assert result.error_message == "rate limited"

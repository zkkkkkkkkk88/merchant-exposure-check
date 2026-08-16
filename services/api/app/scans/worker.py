import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.health import write_worker_heartbeat
from app.db.session import SessionLocal
from app.merchants import models as merchant_models  # noqa: F401
from app.merchants.local_context import process_next_local_context
from app.platform_audits import models as platform_audit_models  # noqa: F401
from app.platform_audits.amap import AmapClient
from app.platform_audits.tencent_maps import TencentMapClient
from app.platform_audits.worker import process_next_platform_audit
from app.queries.models import Query
from app.scans.adapters.ark import ArkSearchAdapter
from app.scans.adapters.base import (
    AdapterError,
    RetryableAdapterError,
    SearchAdapter,
    SearchRequest,
)
from app.scans.models import Citation, QueryResult, ScanRun

Sleep = Callable[[float], Awaitable[None]]
WorkerStep = tuple[str, Callable[[], Awaitable[UUID | None]]]
ErrorReporter = Callable[[str, Exception], None]
logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


def build_adapter_registry(settings: Settings) -> dict[str, SearchAdapter]:
    api_key = settings.ark_api_key.get_secret_value()
    if not api_key:
        return {}
    return {"ark": ArkSearchAdapter(api_key=api_key, model=settings.ark_model)}


async def run_worker_cycle(
    steps: tuple[WorkerStep, ...],
    report_error: ErrorReporter | None = None,
) -> tuple[UUID | None, ...]:
    results: list[UUID | None] = []
    for name, step in steps:
        try:
            results.append(await step())
        except asyncio.CancelledError:
            raise
        except Exception as error:  # keep one unexpected job from stopping every queue
            if report_error is None:
                logger.exception("Worker step %s failed", name)
            else:
                report_error(name, error)
            results.append(None)
    return tuple(results)


async def process_next_scan(
    session_factory: sessionmaker[Session],
    adapters: Mapping[str, SearchAdapter],
    retry_delays: tuple[float, ...] = (2.0,),
    sleep: Sleep = asyncio.sleep,
) -> UUID | None:
    with session_factory() as session:
        run = session.scalar(
            select(ScanRun)
            .where(ScanRun.status == "queued")
            .order_by(ScanRun.created_at)
            .with_for_update(skip_locked=True)
        )
        if run is None:
            return None
        run.status = "running"
        run.started_at = utc_now()
        session.commit()
        run_id = run.id
        query_set_id = run.query_set_id
        merchant_id = run.merchant_id
        adapter_name = run.adapter_name

    with session_factory() as session:
        query_ids = list(
            session.scalars(
                select(Query.id)
                .where(
                    Query.query_set_id == query_set_id,
                    Query.review_status == "approved",
                    Query.is_enabled.is_(True),
                )
                .order_by(Query.priority, Query.created_at)
            ).all()
        )

    adapter = adapters.get(adapter_name)
    for query_id in query_ids:
        with session_factory() as session:
            existing = session.scalar(
                select(QueryResult.id).where(
                    QueryResult.scan_run_id == run_id,
                    QueryResult.query_id == query_id,
                )
            )
            query = session.get(Query, query_id)
            if existing is not None or query is None:
                continue
            query_text = query.text

        started_at = utc_now()
        attempt_count = 0
        response = None
        error_message = None
        while attempt_count < 2:
            attempt_count += 1
            try:
                if adapter is None:
                    raise ValueError(f"Unknown adapter: {adapter_name}")
                response = await adapter.search(
                    SearchRequest(
                        query=query_text,
                        merchant_id=merchant_id,
                        correlation_id=f"{run_id}:{query_id}",
                    )
                )
                break
            except RetryableAdapterError as error:
                error_message = str(error)
                if attempt_count < 2:
                    delay = retry_delays[min(attempt_count - 1, len(retry_delays) - 1)]
                    await sleep(delay)
            except (AdapterError, httpx.HTTPError, ValueError) as error:
                error_message = str(error)
                break

        finished_at = utc_now()
        with session_factory() as session:
            if response is not None:
                result = QueryResult(
                    scan_run_id=run_id,
                    query_id=query_id,
                    status="success",
                    raw_text=response.raw_text,
                    adapter_name=adapter_name,
                    provider_request_id=response.provider_request_id,
                    attempt_count=attempt_count,
                    started_at=started_at,
                    finished_at=finished_at,
                    citations=[
                        Citation(
                            url=citation.url,
                            domain=urlparse(citation.url).netloc.casefold(),
                            title=citation.title,
                            snippet=citation.snippet,
                        )
                        for citation in response.citations
                    ],
                )
            else:
                result = QueryResult(
                    scan_run_id=run_id,
                    query_id=query_id,
                    status="failed",
                    raw_text=None,
                    adapter_name=adapter_name,
                    attempt_count=attempt_count,
                    error_message=error_message or "Unknown adapter failure",
                    started_at=started_at,
                    finished_at=finished_at,
                )
            session.add(result)
            session.commit()

    with session_factory() as session:
        run = session.get(ScanRun, run_id)
        if run is None:
            return run_id
        success_count = session.scalar(
            select(func.count(QueryResult.id)).where(
                QueryResult.scan_run_id == run_id,
                QueryResult.status == "success",
            )
        ) or 0
        failure_count = session.scalar(
            select(func.count(QueryResult.id)).where(
                QueryResult.scan_run_id == run_id,
                QueryResult.status == "failed",
            )
        ) or 0
        run.success_count = success_count
        run.failure_count = failure_count
        run.status = (
            "completed"
            if failure_count == 0
            else "partial"
            if success_count > 0
            else "failed"
        )
        run.finished_at = utc_now()
        if failure_count:
            run.error_summary = f"{failure_count} question(s) failed"
        session.commit()
    return run_id


def recover_stale_scan_runs(
    session_factory: sessionmaker[Session],
    stale_after_seconds: int = 900,
) -> int:
    cutoff = utc_now() - timedelta(seconds=stale_after_seconds)
    with session_factory() as session:
        stale_runs = list(
            session.scalars(
                select(ScanRun).where(
                    ScanRun.status == "running",
                    ScanRun.started_at.is_not(None),
                    ScanRun.started_at < cutoff,
                )
            )
        )
        if not stale_runs:
            return 0
        finished_at = utc_now()
        for run in stale_runs:
            run.status = "failed"
            run.finished_at = finished_at
            run.error_summary = (
                "Worker stopped before this scan finished; retry is available"
            )
        session.commit()
        return len(stale_runs)


async def run_worker(poll_interval: float = 2.0) -> None:
    settings = get_settings()
    adapters = build_adapter_registry(settings)
    amap_key = settings.amap_key.get_secret_value()
    amap = AmapClient(amap_key) if amap_key else None
    tencent_key = settings.tencent_map_key.get_secret_value()
    tencent_maps = TencentMapClient(tencent_key) if tencent_key else None
    async def keep_heartbeat() -> None:
        while True:
            write_worker_heartbeat(settings.runtime_dir)
            await asyncio.sleep(min(poll_interval, 5.0))

    heartbeat_task = asyncio.create_task(keep_heartbeat())
    try:
        recovered_count = recover_stale_scan_runs(SessionLocal)
        if recovered_count:
            logger.warning("Recovered %s stale scan run(s)", recovered_count)
        while True:
            context_id, audit_id, processed_id = await run_worker_cycle(
                (
                    (
                        "local_context",
                        lambda: process_next_local_context(SessionLocal, adapters.get("ark")),
                    ),
                    (
                        "platform_audit",
                        lambda: process_next_platform_audit(
                            SessionLocal, adapters.get("ark"), amap, tencent_maps
                        ),
                    ),
                    (
                        "scan",
                        lambda: process_next_scan(SessionLocal, adapters),
                    ),
                )
            )
            if processed_id is None and context_id is None and audit_id is None:
                await asyncio.sleep(poll_interval)
    finally:
        heartbeat_task.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat_task


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

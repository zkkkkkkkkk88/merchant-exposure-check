from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.merchants.service import MerchantNotFoundError, MerchantService
from app.queries.models import Query, QuerySet
from app.scans.models import Citation, QueryResult, ScanRun
from app.scans.schemas import ManualResultsCreate


class QuerySetNotFoundError(LookupError):
    pass


class NoApprovedQueriesError(ValueError):
    pass


class ScanNotFoundError(LookupError):
    pass


class InvalidManualResultError(ValueError):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


class ScanService:
    @staticmethod
    def create_run(
        session: Session,
        merchant_id: UUID,
        query_set_id: UUID,
        adapter_name: str,
    ) -> ScanRun:
        if MerchantService.get(session, merchant_id) is None:
            raise MerchantNotFoundError(str(merchant_id))
        query_set = session.get(QuerySet, query_set_id)
        if query_set is None or query_set.merchant_id != merchant_id:
            raise QuerySetNotFoundError(str(query_set_id))

        approved_count = session.scalar(
            select(func.count(Query.id)).where(
                Query.query_set_id == query_set_id,
                Query.review_status == "approved",
                Query.is_enabled.is_(True),
            )
        )
        if not approved_count:
            raise NoApprovedQueriesError("Query set has no approved enabled questions")

        run = ScanRun(
            merchant_id=merchant_id,
            query_set_id=query_set_id,
            adapter_name=adapter_name,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run

    @staticmethod
    def get(session: Session, scan_run_id: UUID) -> ScanRun | None:
        return session.get(ScanRun, scan_run_id)

    @staticmethod
    def list_for_merchant(session: Session, merchant_id: UUID) -> list[ScanRun]:
        return list(
            session.scalars(
                select(ScanRun)
                .where(ScanRun.merchant_id == merchant_id)
                .order_by(ScanRun.created_at.desc())
            )
        )

    @staticmethod
    def add_manual_results(
        session: Session,
        scan_run_id: UUID,
        payload: ManualResultsCreate,
    ) -> ScanRun:
        run = ScanService.get(session, scan_run_id)
        if run is None:
            raise ScanNotFoundError(str(scan_run_id))
        if run.adapter_name != "manual":
            raise InvalidManualResultError("Scan does not use the manual adapter")

        allowed_query_ids = set(
            session.scalars(
                select(Query.id).where(
                    Query.query_set_id == run.query_set_id,
                    Query.review_status == "approved",
                    Query.is_enabled.is_(True),
                )
            ).all()
        )
        supplied_ids = {result.query_id for result in payload.results}
        if not supplied_ids.issubset(allowed_query_ids):
            raise InvalidManualResultError("Manual result query does not belong to scan")

        existing_ids = set(
            session.scalars(
                select(QueryResult.query_id).where(QueryResult.scan_run_id == run.id)
            ).all()
        )
        if supplied_ids & existing_ids:
            raise InvalidManualResultError("Manual result already exists for query")

        now = utc_now()
        if run.started_at is None:
            run.started_at = now
        for item in payload.results:
            session.add(
                QueryResult(
                    scan_run_id=run.id,
                    query_id=item.query_id,
                    status="success",
                    raw_text=item.raw_text,
                    adapter_name="manual",
                    attempt_count=1,
                    started_at=now,
                    finished_at=now,
                    citations=[
                        Citation(
                            url=str(citation.url),
                            domain=urlparse(str(citation.url)).netloc.casefold(),
                            title=citation.title,
                            snippet=citation.snippet,
                        )
                        for citation in item.citations
                    ],
                )
            )
        session.flush()

        success_count = session.scalar(
            select(func.count(QueryResult.id)).where(
                QueryResult.scan_run_id == run.id,
                QueryResult.status == "success",
            )
        ) or 0
        run.success_count = success_count
        run.failure_count = 0
        run.status = "completed" if success_count == len(allowed_query_ids) else "partial"
        run.finished_at = now if run.status == "completed" else None
        session.commit()
        session.refresh(run)
        return run

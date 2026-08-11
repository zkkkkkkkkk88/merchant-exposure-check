from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.contracts import MetricSnapshot
from app.analysis.metrics import calculate_metrics
from app.analysis.service import AnalysisService
from app.merchants.models import Merchant
from app.queries.models import Query
from app.reports.models import ManualCheck
from app.reports.schemas import ManualCheckCreate
from app.scans.models import ScanRun


class ReportService:
    @staticmethod
    def metrics(session: Session, merchant_id: UUID, scan_run_id: UUID) -> MetricSnapshot:
        merchant = session.get(Merchant, merchant_id)
        run = session.get(ScanRun, scan_run_id)
        if merchant is None or run is None or run.merchant_id != merchant_id:
            raise ValueError("Report not found")
        analyzed = []
        for result in run.results:
            analysis = AnalysisService.ensure_result(session, result, merchant)
            analyzed.append(AnalysisService.to_metric_result(session, result, analysis))
        session.commit()
        return calculate_metrics(analyzed, merchant.id)

    @staticmethod
    def compare(
        session: Session, merchant_id: UUID, left_id: UUID, right_id: UUID
    ) -> tuple[MetricSnapshot, MetricSnapshot, dict[str, Decimal]]:
        left = ReportService.metrics(session, merchant_id, left_id)
        right = ReportService.metrics(session, merchant_id, right_id)
        fields = (
            "mention_rate",
            "first_position_rate",
            "task_valid_rate",
            "source_coverage_rate",
        )
        return left, right, {
            field: getattr(right, field) - getattr(left, field) for field in fields
        }

    @staticmethod
    def add_manual_check(
        session: Session, scan_run_id: UUID, payload: ManualCheckCreate
    ) -> ManualCheck:
        run = session.get(ScanRun, scan_run_id)
        query = session.get(Query, payload.query_id)
        if run is None or query is None or query.query_set_id != run.query_set_id:
            raise ValueError("Scan run or query not found")
        check = ManualCheck(
            scan_run_id=scan_run_id,
            query_id=payload.query_id,
            answer_summary=payload.answer_summary,
            mentioned=payload.mentioned,
            position=payload.position,
            sources=[str(url) for url in payload.sources],
        )
        session.add(check)
        session.commit()
        session.refresh(check)
        return check

    @staticmethod
    def list_manual_checks(session: Session, scan_run_id: UUID) -> list[ManualCheck]:
        if session.get(ScanRun, scan_run_id) is None:
            raise ValueError("Scan run not found")
        return list(
            session.scalars(
                select(ManualCheck)
                .where(ManualCheck.scan_run_id == scan_run_id)
                .order_by(ManualCheck.checked_at.desc())
            )
        )

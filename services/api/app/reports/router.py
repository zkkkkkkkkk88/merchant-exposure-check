from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.merchants.models import Merchant
from app.reports.schemas import (
    DashboardRead,
    HistoryRead,
    ManualCheckCreate,
    ManualCheckRead,
    ReportRead,
)
from app.reports.service import ReportService
from app.scans.models import ScanRun

router = APIRouter(tags=["reports"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/merchants/{merchant_id}/dashboard", response_model=DashboardRead)
def get_dashboard(merchant_id: UUID, session: SessionDep) -> DashboardRead:
    merchant = session.get(Merchant, merchant_id)
    run = session.scalar(
        select(ScanRun)
        .where(ScanRun.merchant_id == merchant_id)
        .order_by(ScanRun.created_at.desc())
        .limit(1)
    )
    if merchant is None or run is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    metrics = ReportService.metrics(session, merchant_id, run.id)
    categories = [
        {
            "name": category,
            "rate": value,
            "mentioned": round(float(value) * metrics.valid_query_count),
            "total": metrics.valid_query_count,
        }
        for category, value in metrics.category_coverage.items()
    ]
    return DashboardRead(
        merchant={
            "id": str(merchant.id),
            "name": merchant.name,
            "branchName": merchant.branch_name,
        },
        lastRunAt=run.finished_at or run.created_at,
        metrics={
            "mentionRate": metrics.mention_rate,
            "visibilityStage": metrics.visibility_stage,
            "readinessScore": metrics.readiness_score,
            "profileCompleteness": metrics.profile_completeness,
            "publicVerifiability": metrics.public_verifiability,
            "highIntentHitRate": metrics.high_intent_hit_rate,
            "competitorGapClosure": metrics.competitor_gap_closure,
            "sourceCoverageRate": metrics.source_coverage_rate,
            "validQueryCount": metrics.valid_query_count,
            "totalQueryCount": metrics.total_query_count,
        },
        trend=[
            {
                "label": (run.finished_at or run.created_at).strftime("%m/%d"),
                "target": metrics.readiness_score / 100,
                "benchmark": 0,
            }
        ],
        categories=categories,
        competitors=[
            {
                "name": name,
                "mentions": count,
                "sourceCount": 0,
            }
            for name, count in metrics.competitor_counts.items()
        ],
        actions=[],
    )


@router.get("/merchants/{merchant_id}/reports/{scan_run_id}", response_model=ReportRead)
def get_report(
    merchant_id: UUID,
    scan_run_id: UUID,
    session: SessionDep,
) -> ReportRead:
    try:
        metrics = ReportService.metrics(session, merchant_id, scan_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ReportRead(
        merchant_id=merchant_id,
        scan_run_id=scan_run_id,
        metrics=metrics,
        findings=[],
    )


@router.get("/merchants/{merchant_id}/history", response_model=HistoryRead)
def get_history(
    merchant_id: UUID,
    left: UUID,
    right: UUID,
    session: SessionDep,
) -> HistoryRead:
    try:
        left_metrics, right_metrics, deltas = ReportService.compare(
            session, merchant_id, left, right
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return HistoryRead(left=left_metrics, right=right_metrics, deltas=deltas)


@router.post(
    "/scan-runs/{scan_run_id}/manual-checks",
    response_model=ManualCheckRead,
    status_code=status.HTTP_201_CREATED,
)
def add_manual_check(
    scan_run_id: UUID,
    payload: ManualCheckCreate,
    session: SessionDep,
) -> ManualCheckRead:
    try:
        return ManualCheckRead.model_validate(
            ReportService.add_manual_check(session, scan_run_id, payload)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/scan-runs/{scan_run_id}/manual-checks",
    response_model=list[ManualCheckRead],
)
def list_manual_checks(
    scan_run_id: UUID,
    session: SessionDep,
) -> list[ManualCheckRead]:
    try:
        return [
            ManualCheckRead.model_validate(item)
            for item in ReportService.list_manual_checks(session, scan_run_id)
        ]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.reports.schemas import HistoryRead, ManualCheckCreate, ManualCheckRead, ReportRead
from app.reports.service import ReportService

router = APIRouter(tags=["reports"])
SessionDep = Annotated[Session, Depends(get_session)]


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

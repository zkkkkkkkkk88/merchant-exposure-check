from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.merchants.service import MerchantNotFoundError
from app.scans.schemas import ManualResultsCreate, ScanRunCreate, ScanRunRead
from app.scans.service import (
    InvalidManualResultError,
    NoApprovedQueriesError,
    QuerySetNotFoundError,
    ScanNotFoundError,
    ScanService,
)

router = APIRouter(prefix="/scan-runs", tags=["scans"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", response_model=ScanRunRead, status_code=status.HTTP_201_CREATED)
def create_scan_run(payload: ScanRunCreate, session: SessionDep) -> ScanRunRead:
    try:
        run = ScanService.create_run(
            session,
            payload.merchant_id,
            payload.query_set_id,
            payload.adapter_name,
        )
    except MerchantNotFoundError as error:
        raise HTTPException(status_code=404, detail="Merchant not found") from error
    except QuerySetNotFoundError as error:
        raise HTTPException(status_code=404, detail="Query set not found") from error
    except NoApprovedQueriesError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return ScanRunRead.model_validate(run)


@router.get("/{scan_run_id}", response_model=ScanRunRead)
def get_scan_run(scan_run_id: UUID, session: SessionDep) -> ScanRunRead:
    run = ScanService.get(session, scan_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Scan run not found")
    return ScanRunRead.model_validate(run)


@router.post("/{scan_run_id}/manual-results", response_model=ScanRunRead)
def add_manual_results(
    scan_run_id: UUID,
    payload: ManualResultsCreate,
    session: SessionDep,
) -> ScanRunRead:
    try:
        run = ScanService.add_manual_results(session, scan_run_id, payload)
    except ScanNotFoundError as error:
        raise HTTPException(status_code=404, detail="Scan run not found") from error
    except InvalidManualResultError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return ScanRunRead.model_validate(run)

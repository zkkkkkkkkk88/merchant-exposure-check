from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.access import AdminAccessDep
from app.db.session import get_session
from app.platform_audits.schemas import PlatformAuditAdoptRequest, PlatformAuditResultRead, PlatformAuditRunRead
from app.platform_audits.service import (
    PlatformAuditAdoptionConflict,
    PlatformAuditAdoptionInvalid,
    PlatformAuditResultNotFound,
    PlatformAuditService,
)


router = APIRouter(tags=["platform audits"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/merchants/{merchant_id}/platform-audits",
    response_model=PlatformAuditRunRead,
    status_code=status.HTTP_201_CREATED,
)
def create_platform_audit(
    merchant_id: UUID,
    session: SessionDep,
    _access: AdminAccessDep,
):
    try:
        return PlatformAuditService(session).create_run(merchant_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="merchant not found") from exc


@router.get(
    "/merchants/{merchant_id}/platform-audits/latest",
    response_model=PlatformAuditRunRead,
)
def get_latest_platform_audit(merchant_id: UUID, session: SessionDep):
    run = PlatformAuditService(session).get_latest(merchant_id)
    if run is None:
        raise HTTPException(status_code=404, detail="platform audit not found")
    return run


@router.post(
    "/merchants/{merchant_id}/platform-audits/results/{result_id}/adopt",
    response_model=PlatformAuditResultRead,
)
def adopt_platform_field(
    merchant_id: UUID,
    result_id: UUID,
    payload: PlatformAuditAdoptRequest,
    session: SessionDep,
    _access: AdminAccessDep,
):
    try:
        return PlatformAuditService(session).adopt_field(
            merchant_id, result_id, payload.field_key
        )
    except PlatformAuditResultNotFound as exc:
        raise HTTPException(status_code=404, detail="platform audit result not found") from exc
    except PlatformAuditAdoptionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PlatformAuditAdoptionInvalid as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

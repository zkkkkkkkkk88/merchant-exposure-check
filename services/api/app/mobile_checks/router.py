import os
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.mobile_checks.models import MobileEvidence
from app.mobile_checks.schemas import (
    MobileEvidenceRead,
    MobileRoundCreate,
    MobileRoundRead,
    MobileValidationSetCreate,
    MobileValidationSetRead,
    MobileWorkspaceRead,
)
from app.mobile_checks.service import MobileCheckService, NoApprovedQueriesError

router = APIRouter(tags=["mobile checks"])
SessionDep = Annotated[Session, Depends(get_session)]
ALLOWED_IMAGES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_EVIDENCE_BYTES = 10 * 1024 * 1024


@router.post("/merchants/{merchant_id}/mobile-validation-sets", response_model=MobileValidationSetRead, status_code=status.HTTP_201_CREATED)
def create_validation_set(merchant_id: UUID, session: SessionDep):
    try:
        return MobileCheckService(session).create_validation_set(merchant_id)
    except NoApprovedQueriesError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/merchants/{merchant_id}/mobile-validation-sets/select", response_model=MobileValidationSetRead, status_code=status.HTTP_201_CREATED)
def select_validation_set(merchant_id: UUID, payload: MobileValidationSetCreate, session: SessionDep):
    try:
        return MobileCheckService(session).create_validation_set(merchant_id, payload.query_ids)
    except NoApprovedQueriesError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/merchants/{merchant_id}/mobile-validation-sets", response_model=list[MobileValidationSetRead])
def list_validation_sets(merchant_id: UUID, session: SessionDep):
    return MobileCheckService(session).list_validation_sets(merchant_id)


@router.post("/merchants/{merchant_id}/mobile-check-rounds", response_model=MobileRoundRead, status_code=status.HTTP_201_CREATED)
def create_round(merchant_id: UUID, payload: MobileRoundCreate, session: SessionDep):
    record = MobileCheckService(session).create_round(merchant_id, payload)
    if record is None:
        raise HTTPException(status_code=404, detail="validation set or inherited round not found")
    return record


@router.post("/merchants/{merchant_id}/mobile-check-rounds/{round_id}/confirm", response_model=MobileRoundRead)
def confirm_round(merchant_id: UUID, round_id: UUID, session: SessionDep):
    record = MobileCheckService(session).confirm_round(round_id, merchant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="round not found")
    return record


@router.get("/merchants/{merchant_id}/mobile-checks/workspace", response_model=MobileWorkspaceRead)
def get_workspace(merchant_id: UUID, session: SessionDep):
    try:
        return MobileCheckService(session).get_workspace(merchant_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="merchant not found") from exc


@router.post("/merchants/{merchant_id}/mobile-check-rounds/{round_id}/evidence", response_model=MobileEvidenceRead, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    merchant_id: UUID,
    round_id: UUID,
    session: SessionDep,
    request: Request,
    content: bytes = Body(...),
    x_filename: str = Header(default="evidence"),
):
    record = MobileCheckService(session).get_round(round_id, merchant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="round not found")
    content_type = request.headers.get("content-type", "").split(";", 1)[0]
    suffix = ALLOWED_IMAGES.get(content_type)
    if suffix is None:
        raise HTTPException(status_code=400, detail="only JPEG, PNG and WebP evidence is supported")
    if len(content) > MAX_EVIDENCE_BYTES:
        raise HTTPException(status_code=400, detail="evidence image exceeds 10 MB")
    root = Path(os.getenv("MOBILE_EVIDENCE_DIR", "data/mobile-check-evidence")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{uuid4().hex}{suffix}"
    target.write_bytes(content)
    evidence = MobileEvidence(round_id=record.id, original_name=x_filename, storage_path=str(target), content_type=content_type, size_bytes=len(content))
    try:
        session.add(evidence)
        session.commit()
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return evidence

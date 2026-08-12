from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.merchants.schemas import (
    MerchantCreate,
    MerchantLocalContextRead,
    MerchantProfileParseRequest,
    MerchantProfileRead,
    MerchantProfileWrite,
    MerchantRead,
    MerchantUpdate,
)
from app.merchants.service import MerchantNotFoundError, MerchantService
from app.merchants.models import MerchantLocalContext

router = APIRouter(prefix="/merchants", tags=["merchants"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", response_model=MerchantRead, status_code=status.HTTP_201_CREATED)
def create_merchant(
    payload: MerchantCreate,
    session: SessionDep,
) -> MerchantRead:
    return MerchantRead.model_validate(MerchantService.create(session, payload))


@router.get("", response_model=list[MerchantRead])
def list_merchants(session: SessionDep) -> list[MerchantRead]:
    return [MerchantRead.model_validate(item) for item in MerchantService.list(session)]


@router.get("/{merchant_id}", response_model=MerchantRead)
def get_merchant(
    merchant_id: UUID,
    session: SessionDep,
) -> MerchantRead:
    merchant = MerchantService.get(session, merchant_id)
    if merchant is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return MerchantRead.model_validate(merchant)


@router.patch("/{merchant_id}", response_model=MerchantRead)
def update_merchant(
    merchant_id: UUID,
    payload: MerchantUpdate,
    session: SessionDep,
) -> MerchantRead:
    try:
        merchant = MerchantService.update(session, merchant_id, payload)
    except MerchantNotFoundError as error:
        raise HTTPException(status_code=404, detail="Merchant not found") from error
    return MerchantRead.model_validate(merchant)


@router.get("/{merchant_id}/profile", response_model=MerchantProfileRead)
def get_merchant_profile(merchant_id: UUID, session: SessionDep) -> MerchantProfileRead:
    try:
        return MerchantService.get_profile(session, merchant_id)
    except MerchantNotFoundError as error:
        raise HTTPException(status_code=404, detail="Merchant not found") from error


@router.put("/{merchant_id}/profile", response_model=MerchantProfileRead)
def replace_merchant_profile(
    merchant_id: UUID,
    payload: MerchantProfileWrite,
    session: SessionDep,
) -> MerchantProfileRead:
    try:
        return MerchantService.replace_profile(session, merchant_id, payload)
    except MerchantNotFoundError as error:
        raise HTTPException(status_code=404, detail="Merchant not found") from error


@router.post("/{merchant_id}/profile/parse", response_model=MerchantProfileRead)
def parse_merchant_profile(
    merchant_id: UUID,
    payload: MerchantProfileParseRequest,
    session: SessionDep,
) -> MerchantProfileRead:
    try:
        return MerchantService.parse_profile(session, merchant_id, payload)
    except MerchantNotFoundError as error:
        raise HTTPException(status_code=404, detail="Merchant not found") from error


@router.get("/{merchant_id}/local-context", response_model=MerchantLocalContextRead)
def get_local_context(merchant_id: UUID, session: SessionDep) -> MerchantLocalContextRead:
    context = session.get(MerchantLocalContext, merchant_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Local context not found")
    return MerchantLocalContextRead.model_validate(context)


@router.post("/{merchant_id}/local-context/refresh", response_model=MerchantLocalContextRead)
def refresh_local_context(merchant_id: UUID, session: SessionDep) -> MerchantLocalContextRead:
    merchant = MerchantService.get(session, merchant_id)
    if merchant is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    context = merchant.local_context
    context.status = "pending"
    context.error_message = None
    session.commit()
    session.refresh(context)
    return MerchantLocalContextRead.model_validate(context)

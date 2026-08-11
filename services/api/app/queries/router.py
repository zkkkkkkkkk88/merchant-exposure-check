from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.merchants.service import MerchantNotFoundError, MerchantService
from app.queries.schemas import (
    QueryGenerateRequest,
    QueryRead,
    QuerySetRead,
    QueryUpdate,
)
from app.queries.service import QueryLibraryService, QueryNotFoundError

router = APIRouter(tags=["queries"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/merchants/{merchant_id}/query-sets/generate",
    response_model=QuerySetRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_query_set(
    merchant_id: UUID,
    payload: QueryGenerateRequest,
    session: SessionDep,
) -> QuerySetRead:
    try:
        query_set = QueryLibraryService.generate(session, merchant_id, payload.count)
    except MerchantNotFoundError as error:
        raise HTTPException(status_code=404, detail="Merchant not found") from error
    return QuerySetRead.model_validate(query_set)


@router.get("/merchants/{merchant_id}/query-sets", response_model=list[QuerySetRead])
def list_query_sets(merchant_id: UUID, session: SessionDep) -> list[QuerySetRead]:
    if MerchantService.get(session, merchant_id) is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return [
        QuerySetRead.model_validate(query_set)
        for query_set in QueryLibraryService.list_sets(session, merchant_id)
    ]


@router.patch("/queries/{query_id}", response_model=QueryRead)
def update_query(query_id: UUID, payload: QueryUpdate, session: SessionDep) -> QueryRead:
    try:
        query = QueryLibraryService.update_query(session, query_id, payload)
    except QueryNotFoundError as error:
        raise HTTPException(status_code=404, detail="Query not found") from error
    return QueryRead.model_validate(query)

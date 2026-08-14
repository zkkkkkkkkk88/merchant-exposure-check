from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.health import worker_status
from app.db.session import get_session

router = APIRouter(prefix="/system", tags=["system"])
SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


class IntegrationStatus(BaseModel):
    doubao: bool
    amap: bool
    tencent_map: bool


class SystemStatus(BaseModel):
    status: Literal["ok", "degraded"]
    api: Literal["ok"] = "ok"
    database: Literal["ok", "error"]
    worker: Literal["ok", "offline"]
    integrations: IntegrationStatus


@router.get("/status", response_model=SystemStatus)
def get_system_status(session: SessionDep, settings: SettingsDep) -> SystemStatus:
    try:
        session.execute(text("SELECT 1"))
        database = "ok"
    except SQLAlchemyError:  # The status endpoint must report failure, not become another 500.
        database = "error"

    current_worker_status = worker_status(
        settings.runtime_dir,
        settings.worker_stale_after_seconds,
    )
    integrations = IntegrationStatus(
        doubao=bool(settings.ark_api_key.get_secret_value()),
        amap=bool(settings.amap_key.get_secret_value()),
        tencent_map=bool(settings.tencent_map_key.get_secret_value()),
    )
    overall = "ok" if database == "ok" and current_worker_status == "ok" else "degraded"
    return SystemStatus(
        status=overall,
        database=database,
        worker=current_worker_status,
        integrations=integrations,
    )

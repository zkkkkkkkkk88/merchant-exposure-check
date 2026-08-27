from typing import Annotated, Literal

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.core.config import Settings, get_settings

AccessRole = Literal["admin", "demo"]


class AccessIdentity(BaseModel):
    role: AccessRole


def get_access_identity(
    x_access_role: Annotated[str | None, Header()] = None,
    x_internal_auth: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> AccessIdentity:
    if not settings.access_auth_required:
        return AccessIdentity(role="admin")
    expected = settings.internal_api_secret.get_secret_value()
    if not expected or x_internal_auth != expected or x_access_role not in {"admin", "demo"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access identity")
    return AccessIdentity(role=x_access_role)


AccessIdentityDep = Annotated[AccessIdentity, Depends(get_access_identity)]


def require_admin(identity: AccessIdentityDep) -> AccessIdentity:
    if identity.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Demo access is read-only")
    return identity


AdminAccessDep = Annotated[AccessIdentity, Depends(require_admin)]

import pytest
from fastapi import HTTPException

from app.core.access import AccessIdentity, get_access_identity, require_admin
from app.core.config import Settings


def settings(*, required: bool = True) -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        access_auth_required=required,
        internal_api_secret="server-secret",
    )


def test_valid_internal_admin_identity_is_accepted() -> None:
    identity = get_access_identity("admin", "server-secret", settings())
    assert identity == AccessIdentity(role="admin")
    assert require_admin(identity) == identity


def test_demo_identity_cannot_mutate() -> None:
    identity = get_access_identity("demo", "server-secret", settings())
    with pytest.raises(HTTPException) as error:
        require_admin(identity)
    assert error.value.status_code == 403


@pytest.mark.parametrize(
    ("role", "secret"),
    [("admin", "wrong"), ("owner", "server-secret"), (None, None)],
)
def test_required_auth_rejects_untrusted_headers(role, secret) -> None:
    with pytest.raises(HTTPException) as error:
        get_access_identity(role, secret, settings())
    assert error.value.status_code == 401


def test_local_development_defaults_to_admin_when_auth_is_disabled() -> None:
    assert get_access_identity(None, None, settings(required=False)).role == "admin"

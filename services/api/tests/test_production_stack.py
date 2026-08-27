from pathlib import Path

import yaml


ROOT = Path(__file__).parents[3]


def test_production_stack_keeps_internal_services_private() -> None:
    config = yaml.safe_load(
        (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    )
    services = config["services"]

    assert set(services) == {
        "db",
        "migrate",
        "api",
        "worker",
        "web",
        "gateway",
        "tunnel",
    }
    assert all("ports" not in service for service in services.values())
    assert services["db"]["volumes"] == ["production-db:/var/lib/postgresql/data"]
    assert services["api"]["depends_on"]["migrate"]["condition"] == (
        "service_completed_successfully"
    )
    assert services["api"]["environment"]["ACCESS_AUTH_REQUIRED"] == "true"
    assert services["api"]["environment"]["INTERNAL_API_SECRET"] == "${INTERNAL_API_SECRET}"
    assert services["web"]["environment"]["API_BASE_URL"] == "http://api:8000"
    assert services["web"]["environment"]["ACCESS_AUTH_REQUIRED"] == "true"
    assert services["web"]["environment"]["ACCESS_ADMIN_USERNAME"] == "${ACCESS_ADMIN_USERNAME}"
    assert services["web"]["environment"]["ACCESS_ADMIN_PASSWORD_HASH"] == "${ACCESS_ADMIN_PASSWORD_HASH}"
    assert services["web"]["environment"]["ACCESS_DEMO_USERNAME"] == "${ACCESS_DEMO_USERNAME}"
    assert services["web"]["environment"]["ACCESS_DEMO_PASSWORD_HASH"] == "${ACCESS_DEMO_PASSWORD_HASH}"
    assert services["web"]["environment"]["ACCESS_SESSION_SECRET"] == "${ACCESS_SESSION_SECRET}"
    assert services["web"]["environment"]["INTERNAL_API_SECRET"] == "${INTERNAL_API_SECRET}"
    assert services["tunnel"]["command"][-1] == "http://gateway:80"


def test_gateway_delegates_authentication_to_the_application() -> None:
    caddyfile = (ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")
    config = yaml.safe_load(
        (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    )

    assert "basic_auth" not in caddyfile
    assert "AUTH_USERNAME" not in config["services"]["gateway"].get("environment", {})
    assert "AUTH_PASSWORD_HASH" not in config["services"]["gateway"].get("environment", {})


def test_production_environment_template_uses_role_based_access() -> None:
    template = (ROOT / "deploy" / ".env.production.example").read_text(
        encoding="utf-8"
    )

    for name in (
        "ACCESS_AUTH_REQUIRED=true",
        "ACCESS_ADMIN_USERNAME=admin",
        "ACCESS_ADMIN_PASSWORD_HASH=",
        "ACCESS_DEMO_USERNAME=demo",
        "ACCESS_DEMO_PASSWORD_HASH=",
        "ACCESS_SESSION_SECRET=",
        "INTERNAL_API_SECRET=",
    ):
        assert name in template
    assert "AUTH_USERNAME=" not in template
    assert "AUTH_PASSWORD_HASH=" not in template


def test_production_environment_initializer_writes_role_based_access() -> None:
    script = (ROOT / "scripts" / "init-prod-env.sh").read_text(encoding="utf-8")

    for name in (
        "ACCESS_AUTH_REQUIRED=true",
        "ACCESS_ADMIN_USERNAME=admin",
        "ACCESS_ADMIN_PASSWORD_HASH=",
        "ACCESS_DEMO_USERNAME=demo",
        "ACCESS_DEMO_PASSWORD_HASH=",
        "ACCESS_SESSION_SECRET=",
        "INTERNAL_API_SECRET=",
    ):
        assert name in script
    assert "AUTH_USERNAME=" not in script
    assert "AUTH_PASSWORD_HASH=" not in script


def test_existing_production_environment_can_migrate_without_replacing_database_secrets() -> None:
    script = (ROOT / "scripts" / "configure-prod-access.sh").read_text(
        encoding="utf-8"
    )

    assert "deploy/.env.production" in script
    assert "grep -vE" in script
    assert "POSTGRES_PASSWORD" not in script
    for name in (
        "ACCESS_AUTH_REQUIRED=true",
        "ACCESS_ADMIN_USERNAME=admin",
        "ACCESS_ADMIN_PASSWORD_HASH=",
        "ACCESS_DEMO_USERNAME=demo",
        "ACCESS_DEMO_PASSWORD_HASH=",
        "ACCESS_SESSION_SECRET=",
        "INTERNAL_API_SECRET=",
    ):
        assert name in script


def test_real_production_environment_is_not_tracked() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "deploy/.env.production" in ignored

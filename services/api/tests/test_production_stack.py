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
    assert services["web"]["environment"]["API_BASE_URL"] == "http://api:8000"
    assert services["tunnel"]["command"][-1] == "http://gateway:80"


def test_real_production_environment_is_not_tracked() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "deploy/.env.production" in ignored

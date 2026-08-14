import json
import subprocess
from pathlib import Path


def test_start_script_checks_required_runtime_before_launch(tmp_path: Path) -> None:
    api_dir = tmp_path / "services" / "api"
    python = api_dir / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    (api_dir / ".env").write_text(
        "DATABASE_URL=sqlite+pysqlite:///./merchant-exposure.db\n",
        encoding="utf-8",
    )
    web_dir = tmp_path / "apps" / "web"
    web_dir.mkdir(parents=True)
    (web_dir / "package.json").write_text("{}", encoding="utf-8")

    script = Path(__file__).parents[3] / "scripts" / "start-dev.ps1"
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-Root",
            str(tmp_path),
            "-CheckOnly",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ready"
    assert payload["python"].endswith("python.exe")
    assert payload["environment"].endswith(".env")


def test_cmd_launcher_bypasses_windows_script_policy(tmp_path: Path) -> None:
    api_dir = tmp_path / "services" / "api"
    python = api_dir / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    (api_dir / ".env").write_text(
        "DATABASE_URL=sqlite+pysqlite:///./merchant-exposure.db\n",
        encoding="utf-8",
    )
    web_dir = tmp_path / "apps" / "web"
    web_dir.mkdir(parents=True)
    (web_dir / "package.json").write_text("{}", encoding="utf-8")

    launcher = Path(__file__).parents[3] / "scripts" / "start-dev.cmd"
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(launcher), "-Root", str(tmp_path), "-CheckOnly"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "ready"

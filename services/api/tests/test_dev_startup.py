import json
import subprocess
from pathlib import Path


def _create_minimal_project(root: Path) -> None:
    api_dir = root / "services" / "api"
    python = api_dir / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    (api_dir / ".env").write_text(
        "DATABASE_URL=sqlite+pysqlite:///./merchant-exposure.db\n",
        encoding="utf-8",
    )
    web_dir = root / "apps" / "web"
    web_dir.mkdir(parents=True)
    (web_dir / "package.json").write_text("{}", encoding="utf-8")
    next_entry = web_dir / "node_modules" / "next" / "dist" / "bin" / "next"
    next_entry.parent.mkdir(parents=True)
    next_entry.write_text("", encoding="utf-8")


def test_start_script_checks_required_runtime_before_launch(tmp_path: Path) -> None:
    _create_minimal_project(tmp_path)
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
    assert payload["workerHeartbeat"].endswith("worker-heartbeat.json")
    assert payload["logFiles"] == [
        "api.out.log",
        "api.err.log",
        "worker.out.log",
        "worker.err.log",
        "web.out.log",
        "web.err.log",
    ]
    assert payload["webExecutable"].lower().endswith("node.exe")
    assert payload["webEntryPoint"].endswith("node_modules\\next\\dist\\bin\\next")


def test_cmd_launcher_bypasses_windows_script_policy(tmp_path: Path) -> None:
    _create_minimal_project(tmp_path)
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


def test_start_script_normalizes_windows_path_before_start_process() -> None:
    script = Path(__file__).parents[3] / "scripts" / "start-dev.ps1"
    content = script.read_text(encoding="utf-8")

    assert '[Environment]::SetEnvironmentVariable("PATH", $null, "Process")' in content
    assert '[Environment]::SetEnvironmentVariable("Path", $processPath, "Process")' in content

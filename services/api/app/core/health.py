import json
from datetime import UTC, datetime
from pathlib import Path

HEARTBEAT_FILENAME = "worker-heartbeat.json"


def write_worker_heartbeat(runtime_dir: Path) -> None:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    target = runtime_dir / HEARTBEAT_FILENAME
    temporary = runtime_dir / f"{HEARTBEAT_FILENAME}.tmp"
    temporary.write_text(
        json.dumps({"updated_at": datetime.now(UTC).isoformat()}),
        encoding="utf-8",
    )
    temporary.replace(target)


def worker_status(runtime_dir: Path, stale_after_seconds: int) -> str:
    target = runtime_dir / HEARTBEAT_FILENAME
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        updated_at = datetime.fromisoformat(payload["updated_at"])
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return "offline"
    age = (datetime.now(UTC) - updated_at.astimezone(UTC)).total_seconds()
    return "ok" if age <= stale_after_seconds else "offline"

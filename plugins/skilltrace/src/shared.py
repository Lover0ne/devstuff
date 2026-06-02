"""Shared utilities for Skilltrace. All file writes use these atomic helpers."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def skilltrace_dir() -> Path:
    return Path.home() / ".claude" / "skilltrace"


def skills_dir() -> Path:
    return Path.cwd().resolve() / ".claude" / "skills"


def project_skilltrace_dir() -> Path:
    return Path.cwd().resolve() / ".claude" / "skilltrace"



def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    import os
    os.replace(str(tmp), str(path))



def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")



def receipt(status: str, action: str, file: str) -> dict:
    return {"status": status, "action": action, "file": file, "ts": now_iso()}


def error_receipt(error: str, command: str) -> dict:
    return {"error": error, "command": command}


_SKILLTRACE_MARKER = ".skilltrace"


def write_marker(path: Path, data: dict) -> None:
    import os
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(str(tmp), str(path))


def read_marker(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def find_or_create_project_id(start_dir: Path | None = None) -> tuple[str, Path]:
    start = (start_dir or Path.cwd()).resolve()
    marker = start / _SKILLTRACE_MARKER
    data = read_marker(marker)
    if data and data.get("project_id"):
        return data["project_id"], marker
    project_id = f"proj-{uuid.uuid4().hex[:16]}"
    new_data = {"project_id": project_id, "created": now_iso()}
    write_marker(marker, new_data)
    return project_id, marker

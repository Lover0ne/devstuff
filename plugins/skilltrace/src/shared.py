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
    tmp.replace(path)



def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")



def receipt(status: str, action: str, file: str) -> dict:
    return {"status": status, "action": action, "file": file, "ts": now_iso()}


def error_receipt(error: str, command: str) -> dict:
    return {"error": error, "command": command}


_SKILLTRACE_MARKER = ".skilltrace"


def find_or_create_project_id(start_dir: Path | None = None) -> tuple[str, Path]:
    start = start_dir or Path.cwd()
    current = start.resolve()
    found_marker = None
    while True:
        marker = current / _SKILLTRACE_MARKER
        if marker.exists():
            try:
                data = json.loads(marker.read_text(encoding="utf-8"))
                pid = data.get("project_id")
                if pid:
                    return pid, marker
                found_marker = marker
            except (json.JSONDecodeError, OSError):
                found_marker = marker
            break
        parent = current.parent
        if parent == current:
            break
        current = parent
    target = found_marker or (start.resolve() / _SKILLTRACE_MARKER)
    project_id = f"proj-{uuid.uuid4().hex[:8]}"
    data = {"project_id": project_id, "created": now_iso()}
    target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return project_id, target

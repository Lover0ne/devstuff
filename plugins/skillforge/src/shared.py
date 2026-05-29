"""Shared utilities for Skillforge."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

_PLUGIN_DIR_NAME = "skillforge"


def skillforge_dir() -> Path:
    return Path.home() / ".claude" / _PLUGIN_DIR_NAME


def skills_dir() -> Path:
    return Path.home() / ".claude" / "skills"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def receipt(status: str, action: str, file: str) -> dict:
    return {"status": status, "action": action, "file": file, "ts": now_iso()}


def error_receipt(error: str, command: str) -> dict:
    return {"error": error, "command": command}

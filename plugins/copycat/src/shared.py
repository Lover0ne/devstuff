"""Shared utilities for Copycat. Path helpers, atomic writes, response formatters."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def copycat_dir() -> Path:
    return Path.home() / ".claude" / "copycat"


def templates_dir() -> Path:
    return copycat_dir() / "templates"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(str(tmp), str(path))


def receipt(status: str, action: str, file: str) -> dict:
    return {"status": status, "action": action, "file": file, "ts": now_iso()}


def error_receipt(error: str, command: str) -> dict:
    return {"error": error, "command": command}

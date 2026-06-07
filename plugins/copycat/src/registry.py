"""Template registry — CRUD operations with file locking."""

import json
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path

from src.shared import copycat_dir, now_iso, atomic_write_json, receipt, error_receipt

_MAX_TEMPLATES = 10000


def _registry_path() -> Path:
    return copycat_dir() / "registry.json"


@contextmanager
def _lock(timeout: int = 30):
    lock_path = _registry_path().with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout
    delay = 0.05
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            if time.time() > deadline:
                try:
                    lock_path.unlink()
                except OSError:
                    pass
            time.sleep(delay)
            delay = min(delay * 2, 1.0)
    try:
        yield
    finally:
        try:
            lock_path.unlink()
        except OSError:
            pass


def _empty_registry() -> dict:
    return {"version": 1, "templates": []}


def load_registry() -> dict:
    path = _registry_path()
    if not path.exists():
        return _empty_registry()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "templates" not in data:
            backup = path.with_suffix(".json.old")
            os.replace(str(path), str(backup))
            return _empty_registry()
        return data
    except (json.JSONDecodeError, OSError):
        backup = path.with_suffix(".json.old")
        try:
            os.replace(str(path), str(backup))
        except OSError:
            pass
        return _empty_registry()


def add_entry(entry: dict) -> dict:
    template_id = entry.get("id")
    if not template_id or not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", template_id):
        return error_receipt(f"Invalid template ID: {template_id}", "registry_add")

    with _lock():
        reg = load_registry()
        templates = reg["templates"]

        if len(templates) >= _MAX_TEMPLATES:
            return error_receipt("Registry full", "registry_add")

        existing = next((t for t in templates if t.get("id") == template_id), None)
        ts = now_iso()

        if existing:
            existing.update({
                "name": entry.get("name", existing.get("name", "")),
                "source_skill": entry.get("source_skill", existing.get("source_skill", "")),
                "source_project": entry.get("source_project", existing.get("source_project", "")),
                "mode": entry.get("mode", existing.get("mode", "")),
                "placeholders": entry.get("placeholders", existing.get("placeholders", [])),
                "placeholder_count": entry.get("placeholder_count", existing.get("placeholder_count", 0)),
                "updated": ts,
            })
        else:
            templates.append({
                "id": template_id,
                "name": entry.get("name", ""),
                "source_skill": entry.get("source_skill", ""),
                "source_project": entry.get("source_project", ""),
                "mode": entry.get("mode", ""),
                "placeholders": entry.get("placeholders", []),
                "placeholder_count": entry.get("placeholder_count", 0),
                "created": ts,
                "updated": ts,
            })

        atomic_write_json(_registry_path(), reg)
    return receipt("ok", "registry_updated", str(_registry_path()))


def remove_entry(template_id: str) -> dict:
    with _lock():
        reg = load_registry()
        before = len(reg["templates"])
        reg["templates"] = [t for t in reg["templates"] if t.get("id") != template_id]
        if len(reg["templates"]) == before:
            return error_receipt(f"Template '{template_id}' not found", "registry_remove")
        atomic_write_json(_registry_path(), reg)
    return receipt("ok", "registry_removed", str(_registry_path()))


def list_entries() -> list[dict]:
    return load_registry().get("templates", [])

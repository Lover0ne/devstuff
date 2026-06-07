"""Registry CRUD for Skillforge. Manages .claude/skillforge/registry.json (project-level)."""

import json
import os
import re
import shutil
from contextlib import contextmanager
from pathlib import Path

from src.shared import atomic_write_json, now_iso, receipt, error_receipt, skillforge_dir

_MAX_SKILLS = 10000


def _registry_path() -> Path:
    return skillforge_dir() / "registry.json"


def _lock_path() -> Path:
    return _registry_path().with_suffix(".lock")


_LOCK_TIMEOUT = 30


@contextmanager
def _registry_lock():
    lock = _lock_path()
    lock.parent.mkdir(parents=True, exist_ok=True)
    import time
    fd = None
    delay = 0.05
    deadline = time.monotonic() + _LOCK_TIMEOUT
    while True:
        try:
            fd = open(lock, "x")
            break
        except FileExistsError:
            if time.monotonic() > deadline:
                try:
                    lock.unlink()
                except OSError:
                    pass
                fd = open(lock, "x")
                break
            time.sleep(delay)
            delay = min(delay * 2, 1.0)
    try:
        yield
    finally:
        try:
            if fd:
                fd.close()
            lock.unlink(missing_ok=True)
        except OSError:
            pass


def _empty_registry() -> dict:
    return {"version": 1, "skills": []}


def load_registry() -> dict:
    path = _registry_path()
    if not path.exists():
        reg = _empty_registry()
        atomic_write_json(path, reg)
        return reg
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "skills" not in data:
            raise ValueError("invalid structure")
        return data
    except (json.JSONDecodeError, ValueError, OSError):
        old = path.with_suffix(".json.old")
        if path.exists():
            shutil.copy2(str(path), str(old))
            os.remove(str(path))
        reg = _empty_registry()
        atomic_write_json(path, reg)
        return reg


def _save_registry(data: dict) -> None:
    with _registry_lock():
        atomic_write_json(_registry_path(), data)


def add_entry(entry: dict) -> dict:
    sid = entry.get("id", "")
    if sid and not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", sid):
        return error_receipt(f"Invalid skill ID: {sid}", "registry_add")
    with _registry_lock():
        reg = load_registry()
        existing_idx = None
        for i, skill in enumerate(reg["skills"]):
            if skill["id"] == entry["id"]:
                existing_idx = i
                break
        now = now_iso()
        if existing_idx is not None:
            old = reg["skills"][existing_idx]
            version = old.get("version", 1) + 1
            merged = {**old, **entry, "updated": now, "version": version}
            reg["skills"][existing_idx] = merged
        else:
            if len(reg["skills"]) >= _MAX_SKILLS:
                return error_receipt(f"Registry full ({_MAX_SKILLS} skill limit)", "registry_add")
            new_entry = {
                **entry,
                "created": now,
                "updated": now,
                "version": 1,
            }
            reg["skills"].append(new_entry)
        atomic_write_json(_registry_path(), reg)
    return receipt("ok", "registry_entry_added", str(_registry_path()))


def remove_entry(skill_id: str) -> dict:
    with _registry_lock():
        reg = load_registry()
        original_len = len(reg["skills"])
        reg["skills"] = [s for s in reg["skills"] if s["id"] != skill_id]
        if len(reg["skills"]) == original_len:
            return error_receipt(f"Skill '{skill_id}' not found", "registry_remove")
        atomic_write_json(_registry_path(), reg)
    return receipt("ok", "registry_entry_removed", str(_registry_path()))


def list_entries() -> list:
    reg = load_registry()
    return reg["skills"]

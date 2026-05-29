"""Registry CRUD for Skillforge. Manages ~/.claude/skillforge/registry.json."""

import json
from pathlib import Path

from src.shared import atomic_write_json, now_iso, receipt, error_receipt, skillforge_dir


def _registry_path() -> Path:
    return skillforge_dir() / "registry.json"


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
            path.rename(old)
        reg = _empty_registry()
        atomic_write_json(path, reg)
        return reg


def _save_registry(data: dict) -> None:
    atomic_write_json(_registry_path(), data)


def add_entry(entry: dict) -> dict:
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
        new_entry = {
            **entry,
            "created": now,
            "updated": now,
            "version": 1,
        }
        reg["skills"].append(new_entry)
    _save_registry(reg)
    return receipt("ok", "registry_entry_added", str(_registry_path()))


def remove_entry(skill_id: str) -> dict:
    reg = load_registry()
    original_len = len(reg["skills"])
    reg["skills"] = [s for s in reg["skills"] if s["id"] != skill_id]
    if len(reg["skills"]) == original_len:
        return error_receipt(f"Skill '{skill_id}' not found", "registry_remove")
    _save_registry(reg)
    return receipt("ok", "registry_entry_removed", str(_registry_path()))


def list_entries() -> list:
    reg = load_registry()
    return reg["skills"]

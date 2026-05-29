"""Skill file operations — scaffold, archive, version management for Skillforge."""

import shutil
import uuid
from pathlib import Path

from src.shared import skills_dir, skillforge_dir, error_receipt
from src.registry import load_registry, _save_registry


def _versions_dir() -> Path:
    return skillforge_dir() / "versions"


def _skill_dir(skill_id: str) -> Path:
    return skills_dir() / skill_id


def _skill_path(skill_id: str) -> Path:
    return _skill_dir(skill_id) / "SKILL.md"


def _version_path(skill_id: str, version: int) -> Path:
    return _versions_dir() / skill_id / f"v{version}.md"


def _generate_skill_id() -> str:
    return f"sk-{uuid.uuid4().hex[:8]}"


def _is_safe_id(skill_id: str) -> bool:
    return bool(skill_id) and "/" not in skill_id and "\\" not in skill_id and ".." not in skill_id


def _get_registry_entry(skill_id: str) -> dict | None:
    reg = load_registry()
    for skill in reg["skills"]:
        if skill["id"] == skill_id:
            return skill
    return None


def _archive_current(skill_id: str, version: int) -> Path | None:
    src = _skill_path(skill_id)
    if not src.exists():
        return None
    dst = _version_path(skill_id, version)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def _update_registry(skill_id: str, metadata: dict, version: int) -> None:
    from src.shared import now_iso
    reg = load_registry()
    now = now_iso()
    for i, skill in enumerate(reg["skills"]):
        if skill["id"] == skill_id:
            reg["skills"][i] = {**skill, **metadata, "version": version, "updated": now}
            _save_registry(reg)
            return
    entry = {**metadata, "id": skill_id, "version": version, "created": now, "updated": now}
    reg["skills"].append(entry)
    _save_registry(reg)


def archive_project_skills(project_dir: str) -> int:
    """Archive all skills for a project and remove from registry. Returns count archived."""
    reg = load_registry()
    normalized = project_dir.replace("\\", "/").rstrip("/")
    to_archive = [s for s in reg["skills"] if s.get("project_dir", "").replace("\\", "/").rstrip("/") == normalized]

    for skill in to_archive:
        sid = skill["id"]
        version = int(skill.get("version", 1))
        _archive_current(sid, version)
        skill_dir = _skill_dir(sid)
        if skill_dir.exists():
            shutil.rmtree(skill_dir)

    reg["skills"] = [s for s in reg["skills"] if s not in to_archive]
    _save_registry(reg)
    return len(to_archive)


def prepare_create(metadata: dict) -> dict:
    name = metadata.get("name")
    if not name:
        return error_receipt("Missing skill name", "skill_create")

    project_dir = metadata.get("project_dir", "")
    version = int(metadata.pop("version", 1))
    skill_id = _generate_skill_id()

    skill_dir = _skill_dir(skill_id)
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = _skill_path(skill_id)
    path.write_text("", encoding="utf-8")

    entry_data = {
        **metadata,
        "id": skill_id,
        "project_dir": project_dir,
        "path": f"{skill_id}/SKILL.md",
    }
    _update_registry(skill_id, entry_data, version)

    return {
        "status": "ok",
        "action": "create",
        "skill_id": skill_id,
        "write_to": str(path),
        "version": version,
    }


def prepare_new_version(skill_id: str, change_summary: str = "") -> dict:
    if not _is_safe_id(skill_id):
        return error_receipt(f"Invalid skill ID: {skill_id}", "skill_new_version")
    existing = _get_registry_entry(skill_id)
    if not existing:
        return error_receipt(f"Skill '{skill_id}' not found", "skill_new_version")

    current_version = int(existing.get("version", 1))
    archived = _archive_current(skill_id, current_version)

    path = _skill_path(skill_id)
    path.write_text("", encoding="utf-8")

    new_version = current_version + 1
    update_data = {}
    if change_summary:
        update_data["change_summary"] = change_summary
    _update_registry(skill_id, update_data, new_version)

    result = {
        "status": "ok",
        "action": "new_version",
        "skill_id": skill_id,
        "write_to": str(path),
        "version": new_version,
    }
    if archived:
        result["archived"] = str(archived)
    return result

"""Deterministic skill file operations — scaffold, archive, version management.

AI decides WHAT to do (create/new version). This module does the file IO.
Version scheme: v1, v2, v3... (simple integer, always increments).
"""

import re
import uuid
from pathlib import Path

from src.shared import skills_dir, skilltrace_dir, project_skilltrace_dir, error_receipt, find_or_create_project_id
from src.registry import load_registry, _save_registry

_BODY_MARKER = "<!-- SKILL_BODY -->"


def _versions_dir() -> Path:
    return project_skilltrace_dir() / "versions"


def _skill_dir(skill_id: str) -> Path:
    return skills_dir() / skill_id


def _skill_path(skill_id: str) -> Path:
    return _skill_dir(skill_id) / "SKILL.md"


def _version_path(skill_id: str, version: int) -> Path:
    return _versions_dir() / skill_id / f"v{version}.md"


_WIN_RESERVED = frozenset(
    ["con", "prn", "nul", "aux"] +
    [f"com{i}" for i in range(1, 10)] +
    [f"lpt{i}" for i in range(1, 10)]
)


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if not slug:
        return f"sk-{uuid.uuid4().hex[:8]}"
    if slug in _WIN_RESERVED:
        slug = f"{slug}-skill"
    return slug[:64]


def _generate_skill_id(name: str = "") -> str:
    if name:
        slug = _slugify(name)
        if slug:
            return slug
    return f"sk-{uuid.uuid4().hex[:8]}"


def _is_safe_id(skill_id: str) -> bool:
    if not skill_id:
        return False
    return bool(re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", skill_id))


def _get_registry_entry(skill_id: str) -> dict | None:
    reg = load_registry()
    for skill in reg["skills"]:
        if skill["id"] == skill_id:
            return skill
    return None


def _sanitize_yaml_string(s: str) -> str:
    s = s.replace('\\"', '"').replace("\\\\", "\\")
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", "")
    if s.startswith((":", "'", "{", "[", "*", "&", "!", "|", ">")):
        s = " " + s
    return s


def _scaffold_content(name: str, description: str = "") -> str:
    desc = _sanitize_yaml_string(description) if description else "Use when [trigger]"
    return f'---\nname: {_slugify(name)}\ndescription: "{desc}"\n---\n\n{_BODY_MARKER}\n'


def update_skill_meta(skill_id: str, description: str = "", tags: list = None) -> dict:
    if not _is_safe_id(skill_id):
        return error_receipt(f"Invalid skill ID: {skill_id}", "skill_meta")
    existing = _get_registry_entry(skill_id)
    if not existing:
        return error_receipt(f"Skill '{skill_id}' not found", "skill_meta")
    path = _skill_path(skill_id)
    if not path.exists():
        return error_receipt(f"SKILL.md not found for '{skill_id}'. Write body first.", "skill_meta")
    if _BODY_MARKER in path.read_text(encoding="utf-8"):
        return error_receipt(f"Body not written yet for '{skill_id}'. Edit the marker first.", "skill_meta")

    update_data = {}
    if description:
        update_data["description"] = description
    if tags is not None:
        update_data["tags"] = tags

    if update_data:
        version = int(existing.get("version", 1))
        _update_registry(skill_id, update_data, version)

    path = _skill_path(skill_id)
    if path.exists() and description:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        safe_desc = _sanitize_yaml_string(description)
        for i, line in enumerate(lines):
            if line.startswith("description:"):
                lines[i] = f'description: "{safe_desc}"\n'
                break
        path.write_text("".join(lines), encoding="utf-8")

    return {
        "status": "ok",
        "action": "meta_updated",
        "skill_id": skill_id,
        "description": description,
        "tags": tags or [],
        "instructions": "Metadata saved. Skill is complete.",
    }


def _archive_current(skill_id: str, version: int) -> Path | None:
    src = _skill_path(skill_id)
    if not src.exists():
        return None
    dst = _version_path(skill_id, version)
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        src.rename(dst)
    except OSError as e:
        return {"error": str(e)}
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


def prepare_create(metadata: dict) -> dict:
    name = metadata.get("name")
    if not name:
        return error_receipt("Missing skill name", "skill_create")

    project_id, _ = find_or_create_project_id()
    skill_id = _generate_skill_id(name)

    if _skill_dir(skill_id).exists():
        skill_id = f"{skill_id}-{uuid.uuid4().hex[:4]}"

    skill_dir = _skill_dir(skill_id)
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = _skill_path(skill_id)
    path.write_text(
        _scaffold_content(name),
        encoding="utf-8",
    )

    from src.shared import now_iso
    entry_data = {
        "name": name,
        "id": skill_id,
        "project_id": project_id,
        "path": f"{skill_id}/SKILL.md",
        "version_history": [{"version": 1, "created_at": now_iso()}],
    }
    _update_registry(skill_id, entry_data, 1)

    return {
        "status": "ok",
        "action": "create",
        "skill_id": skill_id,
        "write_to": str(path),
        "version": 1,
        "instructions": "1) Read the file at write_to path. 2) Use Edit tool with old_string='<!-- SKILL_BODY -->' and new_string=your body content. Do NOT use Write tool. Do NOT modify frontmatter above the marker.",
    }


def prepare_new_version(skill_id: str, change_summary: str = "") -> dict:
    if not _is_safe_id(skill_id):
        return error_receipt(f"Invalid skill ID: {skill_id}", "skill_new_version")
    existing = _get_registry_entry(skill_id)
    if not existing:
        return error_receipt(f"Skill '{skill_id}' not found", "skill_new_version")

    try:
        current_version = int(existing.get("version", 1))
    except (ValueError, TypeError):
        current_version = 1
    if current_version < 1 or current_version > 10000:
        return error_receipt(f"Invalid version: {current_version}", "skill_new_version")
    current_path = _skill_path(skill_id)
    incomplete = False
    if current_path.exists():
        try:
            incomplete = _BODY_MARKER in current_path.read_text(encoding="utf-8")
        except OSError as e:
            return error_receipt(f"Cannot read current SKILL.md: {e}", "skill_new_version")
    if incomplete:
        archived = None
    else:
        archived = _archive_current(skill_id, current_version)
        if isinstance(archived, dict) and "error" in archived:
            return error_receipt(f"Failed to archive current version: {archived['error']}", "skill_new_version")
        if current_path.exists() and archived is None:
            return error_receipt("Failed to archive current version", "skill_new_version")

    path = _skill_path(skill_id)
    path.write_text(
        _scaffold_content(
            existing.get("name", skill_id),
            existing.get("description", ""),
        ),
        encoding="utf-8",
    )

    from src.shared import now_iso
    new_version = current_version + 1
    history = existing.get("version_history", [])
    history.append({"version": new_version, "created_at": now_iso()})
    update_data = {"version_history": history}
    if change_summary:
        update_data["change_summary"] = change_summary
    _update_registry(skill_id, update_data, new_version)

    result = {
        "status": "ok",
        "action": "new_version",
        "skill_id": skill_id,
        "write_to": str(path),
        "version": new_version,
        "instructions": "1) Read the file at write_to path. 2) Use Edit tool with old_string='<!-- SKILL_BODY -->' and new_string=your body content. Do NOT use Write tool. Do NOT modify frontmatter above the marker.",
    }
    if archived:
        result["archived"] = str(archived)
    return result

#!/usr/bin/env python3
"""Skillforge CLI — utility skill generation.

Commands:
  setup               SessionStart hook — create directories
  existing-skills     Return existing skills for current project
  status              Show skill counts and project info
  skills              List all skills, filterable by project
  registry --add/--remove/--list   Registry CRUD
  skill-write --prepare JSON       Scaffold skill files
  skill-meta  --set JSON           Update skill description and tags
  dashboard   [--no-open]          Generate and open interactive HTML dashboard
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.shared import receipt, error_receipt, skillforge_dir, skills_dir
from src.config import load_config
from src.registry import add_entry, remove_entry, list_entries
from src.skill_ops import prepare_create, prepare_new_version, update_skill_meta


def cmd_setup() -> dict:
    base = skillforge_dir()
    dirs = [base, base / "versions", skills_dir()]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    load_config()
    result = receipt("ok", "setup_complete", str(base))
    result["additionalContext"] = "Skillforge ready. Use /skillforge-launch to generate utility skills for this project."
    return result


def cmd_existing_skills() -> list:
    """Return existing skills for current project directory with descriptions."""
    entries = list_entries()
    cwd = os.getcwd().replace("\\", "/").rstrip("/")
    project_skills = [e for e in entries if e.get("project_dir", "").replace("\\", "/").rstrip("/") == cwd]
    result = []
    for e in project_skills:
        info = {
            "id": e.get("id"),
            "name": e.get("name"),
            "category": e.get("category", ""),
            "version": e.get("version", 1),
        }
        skill_path = skills_dir() / e.get("id", "") / "SKILL.md"
        if skill_path.exists():
            try:
                for line in skill_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("description:"):
                        info["description"] = line.split(":", 1)[1].strip().strip('"')
                        break
            except Exception:
                pass
        result.append(info)
    return result


def cmd_archive_project() -> dict:
    """Archive all skills for current project, clear from registry. Returns count."""
    from src.skill_ops import archive_project_skills
    cwd = os.getcwd().replace("\\", "/").rstrip("/")
    count = archive_project_skills(cwd)
    return receipt("ok", "archive_project", f"{count} skills archived")


def cmd_status() -> dict:
    entries = list_entries()
    cwd = os.getcwd().replace("\\", "/").rstrip("/")
    project_skills = [e for e in entries if e.get("project_dir", "").replace("\\", "/").rstrip("/") == cwd]
    last_updated = max((e.get("updated", "") for e in entries), default="never")
    return {
        "total_skills": len(entries),
        "project_skills": len(project_skills),
        "project_dir": cwd,
        "last_updated": last_updated,
    }


def cmd_skills() -> dict:
    entries = list_entries()
    cwd = os.getcwd().replace("\\", "/").rstrip("/")

    skills_list = []
    for e in entries:
        info = {
            "id": e.get("id"),
            "name": e.get("name"),
            "version": e.get("version", 1),
            "category": e.get("category", ""),
            "project_dir": e.get("project_dir", ""),
            "is_current_project": e.get("project_dir", "").replace("\\", "/").rstrip("/") == cwd,
            "created": e.get("created", ""),
            "updated": e.get("updated", ""),
        }
        skill_path = skills_dir() / e.get("id", "") / "SKILL.md"
        if skill_path.exists():
            try:
                for line in skill_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("description:"):
                        info["description"] = line.split(":", 1)[1].strip().strip('"')
                        break
            except Exception:
                pass
        skills_list.append(info)

    return {
        "total": len(entries),
        "this_project": sum(1 for s in skills_list if s.get("is_current_project")),
        "other_projects": sum(1 for s in skills_list if not s.get("is_current_project")),
        "skills": skills_list,
    }


def cmd_registry_add(entry_json: str) -> dict:
    try:
        entry = json.loads(entry_json)
    except json.JSONDecodeError as e:
        return error_receipt(f"Invalid JSON: {e}", "registry_add")
    return add_entry(entry)


def cmd_registry_remove(skill_id: str) -> dict:
    if not skill_id or "/" in skill_id or "\\" in skill_id or ".." in skill_id:
        return error_receipt(f"Invalid skill ID: {skill_id}", "registry_remove")
    return remove_entry(skill_id)


def cmd_registry_list() -> list:
    return list_entries()


def cmd_skill_write(metadata_json: str) -> dict:
    try:
        meta = json.loads(metadata_json)
    except json.JSONDecodeError as e:
        return error_receipt(f"Invalid JSON: {e}", "skill_write")
    action = meta.pop("action", "")
    if action == "create":
        return prepare_create(meta)
    elif action == "new_version":
        skill_id = meta.get("id")
        if not skill_id:
            return error_receipt("Missing skill id", "skill_write")
        return prepare_new_version(skill_id, meta.get("change_summary", ""))
    else:
        return error_receipt(f"Unknown action: {action}. Use create/new_version.", "skill_write")


def main():
    if len(sys.argv) < 2:
        print(json.dumps(error_receipt("No command provided", "cli")), file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "setup":
            result = cmd_setup()
            print(json.dumps(result))

        elif command == "existing-skills":
            result = cmd_existing_skills()
            print(json.dumps(result))

        elif command == "archive-project":
            result = cmd_archive_project()
            print(json.dumps(result))

        elif command == "status":
            result = cmd_status()
            print(json.dumps(result))

        elif command == "skills":
            result = cmd_skills()
            print(json.dumps(result))

        elif command == "registry":
            if len(sys.argv) < 3:
                print(json.dumps(error_receipt("Registry subcommand required", "registry")), file=sys.stderr)
                sys.exit(1)
            subcmd = sys.argv[2]
            if subcmd == "--add":
                entry_json = sys.argv[3] if len(sys.argv) > 3 else sys.stdin.read()
                result = cmd_registry_add(entry_json)
                print(json.dumps(result))
            elif subcmd == "--remove":
                if len(sys.argv) < 4:
                    print(json.dumps(error_receipt("Skill ID required", "registry_remove")), file=sys.stderr)
                    sys.exit(1)
                result = cmd_registry_remove(sys.argv[3])
                print(json.dumps(result))
            elif subcmd == "--list":
                result = cmd_registry_list()
                print(json.dumps(result))
            else:
                print(json.dumps(error_receipt(f"Unknown registry subcommand: {subcmd}", "registry")), file=sys.stderr)
                sys.exit(1)

        elif command == "skill-write":
            if len(sys.argv) < 3 or sys.argv[2] != "--prepare":
                print(json.dumps(error_receipt("Usage: skill-write --prepare JSON", "skill_write")), file=sys.stderr)
                sys.exit(1)
            metadata_json = sys.argv[3] if len(sys.argv) > 3 else sys.stdin.read()
            result = cmd_skill_write(metadata_json)
            print(json.dumps(result))

        elif command == "skill-meta":
            if len(sys.argv) < 3 or sys.argv[2] != "--set":
                print(json.dumps(error_receipt("Usage: skill-meta --set JSON", "skill_meta")), file=sys.stderr)
                sys.exit(1)
            meta_json = sys.argv[3] if len(sys.argv) > 3 else sys.stdin.read()
            try:
                meta = json.loads(meta_json)
            except json.JSONDecodeError as e:
                print(json.dumps(error_receipt(f"Invalid JSON: {e}", "skill_meta")), file=sys.stderr)
                sys.exit(1)
            skill_id = meta.get("id")
            if not skill_id:
                print(json.dumps(error_receipt("Missing skill id", "skill_meta")), file=sys.stderr)
                sys.exit(1)
            result = update_skill_meta(skill_id, meta.get("description", ""), meta.get("tags"))
            print(json.dumps(result))

        elif command == "dashboard":
            from src.dashboard import generate
            no_open = "--no-open" in sys.argv
            result = generate(no_open=no_open)
            print(json.dumps(result))

        else:
            print(json.dumps(error_receipt(f"Unknown command: {command}", "cli")), file=sys.stderr)
            sys.exit(1)

    except json.JSONDecodeError as e:
        print(json.dumps(error_receipt(f"Invalid JSON input: {e}", command)), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps(error_receipt(f"{type(e).__name__}: {e}", command)), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Skilltrace CLI — skill extraction and registry management.

Commands:
  setup                     First-run directory creation (SessionStart hook)
  init                      Enable Skilltrace for current project
  skip                      Decline Skilltrace for current project
  reminder                  UserPromptSubmit hook — arm task boundary gate
  finalize                  SessionEnd hook — trigger skilltracer for last task
  pause                     Disable activity tracking
  resume                    Enable activity tracking
  status                    Show plugin status and skill count
  skills                    List all skills with descriptions and versions
  history <skill-id>        Show version history of a skill
  overview                  Show skills across all projects
  reindex                   Rebuild registry from SKILL.md files on disk
  scrape-transcript --stdin Scrape transcript JSONL, return clean JSON array
  registry        --add/--remove/--list   Registry CRUD operations
  skill-write     --prepare JSON   Scaffold skill files, archive old versions
  skill-meta      --set JSON      Update skill description and tags
  dashboard       [--no-open]     Generate and open interactive HTML dashboard
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.shared import receipt, error_receipt, skilltrace_dir, skills_dir, project_skilltrace_dir, find_or_create_project_id, now_iso
from src.config import load_config, is_enabled, set_enabled
from src.registry import add_entry, remove_entry, list_entries
from src.transcript import scrape_transcript
from src.skill_ops import prepare_create, prepare_new_version, update_skill_meta


def _find_marker() -> Path | None:
    marker = Path.cwd().resolve() / ".skilltrace"
    return marker if marker.exists() else None


def _check_marker_exists() -> bool:
    return _find_marker() is not None


def cmd_setup() -> dict:
    base = skilltrace_dir()
    cfg_path = base / "config.json"
    first_run = not cfg_path.exists()

    base.mkdir(parents=True, exist_ok=True)
    skills_dir().mkdir(parents=True, exist_ok=True)
    project_skilltrace_dir().mkdir(parents=True, exist_ok=True)
    (project_skilltrace_dir() / "versions").mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    status = "active" if cfg.get("enabled", True) else "dormant"
    result = receipt("ok", "setup_complete", str(base))
    result["status"] = status

    if first_run:
        result["additionalContext"] = (
            "Skilltrace installed. It automatically traces your work and converts "
            "completed tasks into replayable skills stored in .claude/skills/. "
            "Runs silently in background — zero overhead. "
            "Disable anytime with /skilltrace-pause."
        )
    elif status == "active":
        result["additionalContext"] = "Skilltrace active."

    return result


def cmd_init() -> dict:
    project_id, marker = find_or_create_project_id()
    return {
        "status": "ok",
        "action": "project_initialized",
        "project_id": project_id,
        "additionalContext": (
            f"Skilltrace enabled for this project (ID: {project_id}). "
            "Skills will be generated automatically."
        ),
    }


def cmd_skip() -> dict:
    current = Path.cwd().resolve()
    marker = current / ".skilltrace"
    if marker.exists():
        try:
            data = json.loads(marker.read_text(encoding="utf-8"))
            if data.get("project_id"):
                return receipt("ok", "already_initialized", str(marker))
        except Exception:
            pass
    data = {"declined": True, "created": now_iso()}
    marker.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return receipt("ok", "skipped", str(marker))


def cmd_scrape_transcript(transcript_path: str) -> list:
    if not transcript_path or not transcript_path.strip():
        return []
    return scrape_transcript(transcript_path.strip())


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


def cmd_registry_list(project_only: bool = False) -> dict:
    entries = list_entries()
    if project_only:
        project_id = _read_project_id()
        if project_id:
            entries = [e for e in entries if e.get("project_id") == project_id]
    return {
        "skills": entries,
        "count": len(entries),
        "instructions": (
            "Compare each skill against the work done. "
            "For matches: bash \"${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh\" skill-write --prepare '{\"action\":\"new_version\",\"id\":\"SKILL_ID\",\"change_summary\":\"WHAT_CHANGED\"}' "
            "For uncovered work: bash \"${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh\" skill-write --prepare '{\"action\":\"create\",\"name\":\"SKILL_NAME\",\"description\":\"Use when TRIGGER\",\"tags\":[\"tag1\"]}' "
            "Always include description field. Then follow the instructions in the response."
        ),
    }


def cmd_reminder(hook_data: dict) -> dict:
    if not _check_marker_exists():
        return {}
    project_id = _read_project_id()
    if not project_id:
        return {}
    tp = hook_data.get("transcript_path", "")
    cwd = os.getcwd()
    pending_dir = Path.home() / ".skilltrace-gate"
    pending_dir.mkdir(parents=True, exist_ok=True)
    deny_response = json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "[SKILLTRACE] Spawn the skilltracer agent now "
                "(Agent tool, run_in_background=true) with prompt including: "
                "1) detailed summary of the task — what you did, what changed, files involved. "
                "If subagents were used, include what EACH subagent did and what files it modified. "
                f"2) transcript_path={tp} "
                f"3) project_dir={cwd} "
                "4) 'Follow the skilltracer agent procedure from the skilltrace plugin.' "
                "Then retry your tool call."
            )
        }
    })
    (pending_dir / "pending").write_text(deny_response, encoding="utf-8")
    return {}


def cmd_finalize(hook_data: dict) -> dict:
    tp = hook_data.get("transcript_path", "")
    cwd = os.getcwd()
    return {"additionalContext": (
        "Session ending. Spawn the skilltracer agent in background. "
        "In the agent prompt include: "
        "1) detailed summary of the task — what you did, what changed, files involved. "
        "If subagents were used, include what EACH subagent did and what files it modified. "
        f"2) transcript_path={tp} "
        f"3) project_dir={cwd} "
        "4) 'Follow the skilltracer agent procedure from the skilltrace plugin.'"
    )}


def cmd_pause() -> dict:
    marker = _find_marker()
    if not marker:
        return error_receipt("No .skilltrace marker found. Run /skilltrace-init first.", "pause")
    data = json.loads(marker.read_text(encoding="utf-8"))
    data["paused"] = True
    marker.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return receipt("ok", "paused", str(marker))


def cmd_resume() -> dict:
    marker = _find_marker()
    if not marker:
        return error_receipt("No .skilltrace marker found. Run /skilltrace-init first.", "resume")
    data = json.loads(marker.read_text(encoding="utf-8"))
    data.pop("paused", None)
    marker.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return receipt("ok", "resumed", str(marker))


def _read_project_id() -> str | None:
    marker = _find_marker()
    if not marker:
        return None
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
        return data.get("project_id")
    except Exception:
        return None


def cmd_status() -> dict:
    entries = list_entries()
    project_id = _read_project_id()
    marker = _find_marker()
    paused = False
    if marker:
        try:
            paused = json.loads(marker.read_text(encoding="utf-8")).get("paused", False)
        except Exception:
            pass
    project_skills = [e for e in entries if e.get("project_id") == project_id] if project_id else []
    last_updated = max((e.get("updated", "") for e in entries), default="never")
    result = {
        "enabled": not paused,
        "total_skills": len(entries),
        "project_skills": len(project_skills),
        "project_id": project_id or "not initialized",
        "last_updated": last_updated,
    }
    if not project_id:
        result["additionalContext"] = "Project not initialized. Use /skilltrace-init to enable."
    return result


def cmd_skills() -> dict:
    entries = list_entries()
    project_id = _read_project_id()

    skills_list = []
    for e in entries:
        is_current = e.get("project_id") == project_id if project_id else False
        skills_list.append({
            "id": e.get("id"),
            "name": e.get("name"),
            "description": e.get("description", ""),
            "version": e.get("version", 1),
            "project_id": e.get("project_id"),
            "is_current_project": is_current,
            "created": e.get("created", ""),
            "updated": e.get("updated", ""),
        })

    return {
        "total": len(entries),
        "this_project": sum(1 for s in skills_list if s.get("is_current_project")),
        "other_projects": sum(1 for s in skills_list if not s.get("is_current_project")),
        "skills": skills_list,
    }


def cmd_reindex() -> dict:
    sdir = skills_dir()
    if not sdir.exists():
        return receipt("ok", "reindex", "0 skills found")
    project_id = _read_project_id() or "unknown"
    count = 0
    for skill_dir in sdir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        skill_id = skill_dir.name
        content = skill_file.read_text(encoding="utf-8")
        name = skill_id
        description = ""
        for line in content.splitlines():
            if line.startswith("# "):
                name = line[2:].strip()
            if line.startswith("description:"):
                description = line.split(":", 1)[1].strip().strip('"')
        add_entry({
            "id": skill_id,
            "name": name,
            "description": description,
            "tags": [],
            "project_id": project_id,
        })
        count += 1
    return receipt("ok", "reindex", f"{count} skills indexed")


def cmd_history(skill_id: str) -> dict:
    if not skill_id:
        return error_receipt("Skill ID required", "history")
    entries = list_entries()
    entry = next((e for e in entries if e.get("id") == skill_id), None)
    if not entry:
        return error_receipt(f"Skill '{skill_id}' not found in registry", "history")

    current_path = skills_dir() / skill_id / "SKILL.md"
    versions_base = project_skilltrace_dir() / "versions" / skill_id
    current_version = entry.get("version", 1)

    history = []
    for v in range(1, current_version):
        vpath = versions_base / f"v{v}.md"
        if vpath.exists():
            content = vpath.read_text(encoding="utf-8")
            history.append({"version": v, "content": content})

    if current_path.exists():
        content = current_path.read_text(encoding="utf-8")
        history.append({"version": current_version, "content": content, "current": True})

    return {
        "skill_id": skill_id,
        "name": entry.get("name"),
        "current_version": current_version,
        "project_id": entry.get("project_id"),
        "created": entry.get("created", ""),
        "updated": entry.get("updated", ""),
        "versions": history,
    }


def cmd_overview() -> dict:
    entries = list_entries()
    projects = {}
    for e in entries:
        pid = e.get("project_id", "unknown")
        if pid not in projects:
            projects[pid] = []
        projects[pid].append({
            "id": e.get("id"),
            "name": e.get("name"),
            "description": e.get("description", ""),
            "version": e.get("version", 1),
            "created": e.get("created", ""),
            "updated": e.get("updated", ""),
        })

    current_project_id = _read_project_id()
    return {
        "current_project_id": current_project_id or "not initialized",
        "total_skills": len(entries),
        "total_projects": len(projects),
        "projects": projects,
    }


def cmd_dashboard() -> dict:
    from src.dashboard import generate
    no_open = "--no-open" in sys.argv
    return generate(no_open=no_open)


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


def cmd_skill_meta(meta_json: str) -> dict:
    try:
        meta = json.loads(meta_json)
    except json.JSONDecodeError as e:
        return error_receipt(f"Invalid JSON: {e}", "skill_meta")
    skill_id = meta.get("id")
    if not skill_id:
        return error_receipt("Missing skill id", "skill_meta")
    return update_skill_meta(
        skill_id,
        description=meta.get("description", ""),
        tags=meta.get("tags"),
    )


def main():
    if len(sys.argv) < 2:
        print(json.dumps(error_receipt("No command provided", "cli")), file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    always_allowed = ("setup", "init", "skip", "registry", "pause", "resume", "status", "skills", "reindex", "history", "overview", "dashboard", "scrape-transcript", "skill-write", "skill-meta")
    if not is_enabled() and command not in always_allowed:
        if command in ("reminder", "finalize"):
            print(json.dumps({}))
            sys.exit(0)
        print(json.dumps({"exit": 2, "reason": "disabled"}))
        sys.exit(2)

    try:
        if command == "setup":
            result = cmd_setup()
            print(json.dumps(result))

        elif command == "scrape-transcript":
            transcript_path = sys.stdin.read().strip()
            result = cmd_scrape_transcript(transcript_path)
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
                project_flag = "--project" in sys.argv
                result = cmd_registry_list(project_only=project_flag)
                print(json.dumps(result))
            else:
                print(json.dumps(error_receipt(f"Unknown registry subcommand: {subcmd}", "registry")), file=sys.stderr)
                sys.exit(1)
        elif command == "reminder":
            hook_data = json.loads(sys.stdin.read())
            result = cmd_reminder(hook_data)
            print(json.dumps(result))

        elif command == "finalize":
            hook_data = json.loads(sys.stdin.read())
            result = cmd_finalize(hook_data)
            print(json.dumps(result))

        elif command == "pause":
            result = cmd_pause()
            print(json.dumps(result))

        elif command == "resume":
            result = cmd_resume()
            print(json.dumps(result))

        elif command == "status":
            result = cmd_status()
            print(json.dumps(result))

        elif command == "init":
            result = cmd_init()
            print(json.dumps(result))

        elif command == "skip":
            result = cmd_skip()
            print(json.dumps(result))

        elif command == "skills":
            result = cmd_skills()
            print(json.dumps(result))

        elif command == "reindex":
            result = cmd_reindex()
            print(json.dumps(result))

        elif command == "history":
            if len(sys.argv) < 3:
                print(json.dumps(error_receipt("Skill ID required", "history")), file=sys.stderr)
                sys.exit(1)
            result = cmd_history(sys.argv[2])
            print(json.dumps(result))

        elif command == "overview":
            result = cmd_overview()
            print(json.dumps(result))

        elif command == "dashboard":
            result = cmd_dashboard()
            print(json.dumps(result))

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
            result = cmd_skill_meta(meta_json)
            print(json.dumps(result))
        else:
            print(json.dumps(error_receipt(f"Unknown command: {command}", "cli")), file=sys.stderr)
            sys.exit(1)

    except json.JSONDecodeError as e:
        print(json.dumps(error_receipt(f"Invalid JSON input: {e}", command)), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps(error_receipt(str(e), command)), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

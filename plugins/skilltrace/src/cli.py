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

from src.shared import receipt, error_receipt, skilltrace_dir, skills_dir, project_skilltrace_dir, find_or_create_project_id, now_iso, write_marker, read_marker
from src.config import load_config, is_enabled
from src.registry import add_entry, remove_entry, list_entries
from src.transcript import _scrape_transcript_impl
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

    cfg = load_config()
    status = "active" if cfg.get("enabled", True) else "dormant"
    result = receipt("ok", "setup_complete", str(base))
    result["status"] = status

    if first_run:
        result["additionalContext"] = (
            "Skilltrace installed. It automatically traces your work and converts "
            "completed tasks into replayable skills stored in .claude/skills/. "
            "Runs silently in background — zero overhead. "
            "Disable anytime with /skilltrace-stop."
        )
    elif status == "active":
        result["additionalContext"] = "Skilltrace active."

    return result


def cmd_init(project_dir: str | None = None) -> dict:
    if project_dir:
        os.chdir(project_dir)
    project_id, marker = find_or_create_project_id()
    skills_dir().mkdir(parents=True, exist_ok=True)
    project_skilltrace_dir().mkdir(parents=True, exist_ok=True)
    (project_skilltrace_dir() / "versions").mkdir(parents=True, exist_ok=True)
    suppress_dir = Path.home() / ".skilltrace-gate"
    suppress_dir.mkdir(parents=True, exist_ok=True)
    (suppress_dir / "suppress").write_text("1", encoding="utf-8")
    return {
        "status": "ok",
        "action": "project_initialized",
        "project_id": project_id,
        "additionalContext": (
            f"Skilltrace enabled for this project (ID: {project_id}). "
            "Skills will be generated automatically."
        ),
    }


def cmd_skip(project_dir: str | None = None) -> dict:
    if project_dir:
        os.chdir(project_dir)
    current = Path.cwd().resolve()
    marker = current / ".skilltrace"
    existing = read_marker(marker)
    if existing and existing.get("project_id"):
        return receipt("ok", "already_initialized", str(marker))
    write_marker(marker, {"declined": True, "created": now_iso()})
    return receipt("ok", "skipped", str(marker))


def cmd_scrape_transcript(transcript_path: str) -> list:
    if not transcript_path or not transcript_path.strip():
        return []
    tp = transcript_path.strip()
    marker = _find_marker()
    marker_data = read_marker(marker) if marker else None
    lower = None
    if marker_data:
        ltb = marker_data.get("last_traced_boundary")
        if isinstance(ltb, dict) and ltb.get("transcript") == tp:
            lower = ltb.get("index")
    entries, new_boundary = _scrape_transcript_impl(tp, lower_boundary=lower)
    if marker and marker_data is not None and new_boundary is not None:
        marker_data["last_traced_boundary"] = {"transcript": tp, "index": new_boundary}
        write_marker(marker, marker_data)
    return entries


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
            "For uncovered work: bash \"${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh\" skill-write --prepare '{\"action\":\"create\",\"name\":\"SKILL_NAME\"}' "
            "Then follow the instructions in the response. Description and tags are set later via skill-meta."
        ),
    }


def cmd_reminder(hook_data: dict) -> dict:
    if not _check_marker_exists():
        return {}
    marker = _find_marker()
    marker_data = read_marker(marker) if marker else None
    if not marker_data:
        return {}
    if marker_data.get("paused"):
        return {}
    project_id = marker_data.get("project_id")
    if not project_id:
        return {}
    suppress_file = Path.home() / ".skilltrace-gate" / "suppress"
    if suppress_file.exists():
        suppress_file.unlink()
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
                "1) detailed summary of the SINGLE most recent completed task only (NOT the current task you are about to do). "
                "Describe what was built, changed, or fixed in the immediately previous prompt. "
                "Do NOT include tasks from earlier prompts — only the last one. "
                "If subagents were used for that task, include what EACH subagent did and what files it modified. "
                "EXCLUDE any skilltrace commands or skill management operations from the summary. "
                "If no real work was done in the previous prompt, say 'No significant work to evaluate'. "
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
    if not _check_marker_exists():
        return {}
    marker = _find_marker()
    marker_data = read_marker(marker) if marker else None
    if not marker_data or marker_data.get("paused") or marker_data.get("declined") or not marker_data.get("project_id"):
        return {}
    tp = hook_data.get("transcript_path", "")
    cwd = os.getcwd()
    return {"additionalContext": (
        "Session ending. Spawn the skilltracer agent in background. "
        "In the agent prompt include: "
        "1) detailed summary of ALL work done in this session — what was built, changed, or fixed. "
        "If subagents were used, include what EACH subagent did and what files it modified. "
        "EXCLUDE any skilltrace commands or skill management operations from the summary. "
        f"2) transcript_path={tp} "
        f"3) project_dir={cwd} "
        "4) 'Follow the skilltracer agent procedure from the skilltrace plugin.'"
    )}


def cmd_stop() -> dict:
    marker = _find_marker()
    if not marker:
        return error_receipt("No .skilltrace marker found. The gate will handle initialization.", "stop")
    data = read_marker(marker) or {}
    if data.get("declined"):
        return error_receipt("Skilltrace is already inactive (declined).", "stop")
    data["paused"] = True
    write_marker(marker, data)
    return receipt("ok", "stopped", str(marker))


def cmd_start() -> dict:
    marker = _find_marker()
    if not marker:
        return error_receipt("No .skilltrace marker found. The gate will handle initialization on next tool use.", "start")
    data = read_marker(marker) or {}
    if data.get("declined"):
        import uuid
        data.pop("declined", None)
        project_id = f"proj-{uuid.uuid4().hex[:16]}"
        data["project_id"] = project_id
        data["created"] = now_iso()
        write_marker(marker, data)
        skills_dir().mkdir(parents=True, exist_ok=True)
        project_skilltrace_dir().mkdir(parents=True, exist_ok=True)
        (project_skilltrace_dir() / "versions").mkdir(parents=True, exist_ok=True)
        return {
            "status": "ok",
            "action": "enabled",
            "project_id": project_id,
            "file": str(marker),
            "ts": now_iso(),
            "additionalContext": f"Skilltrace enabled (ID: {project_id}). Was previously declined, now active.",
        }
    if data.get("paused"):
        data.pop("paused", None)
        write_marker(marker, data)
        return receipt("ok", "resumed", str(marker))
    return receipt("ok", "already_active", str(marker))


def _read_project_id() -> str | None:
    marker = _find_marker()
    if not marker:
        return None
    data = read_marker(marker)
    return data.get("project_id") if data else None


def cmd_skills() -> dict:
    entries = list_entries()
    project_id = _read_project_id()
    marker = _find_marker()
    marker_data = read_marker(marker) if marker else None

    if marker_data and marker_data.get("paused"):
        current_status = "paused"
    elif marker_data and marker_data.get("project_id"):
        current_status = "active"
    else:
        current_status = "not initialized"

    projects = {}
    for e in entries:
        pid = e.get("project_id", "unknown")
        if pid not in projects:
            projects[pid] = {"skills": [], "is_current": pid == project_id}
        projects[pid]["skills"].append({
            "id": e.get("id"),
            "name": e.get("name"),
            "description": e.get("description", ""),
            "version": e.get("version", 1),
            "created": e.get("created", ""),
            "updated": e.get("updated", ""),
        })

    return {
        "current_project": {
            "id": project_id or "not initialized",
            "status": current_status,
        },
        "total_skills": len(entries),
        "total_projects": len(projects),
        "projects": projects,
    }


def cmd_reindex() -> dict:
    sdir = skills_dir()
    if not sdir.exists():
        return receipt("ok", "reindex", "0 skills found")
    project_id = _read_project_id() or "unknown"
    existing_entries = {e["id"]: e for e in list_entries()}
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
        existing = existing_entries.get(skill_id)
        if existing and existing.get("name") == name and existing.get("description") == description:
            continue
        existing_tags = existing.get("tags", []) if existing else []
        add_entry({
            "id": skill_id,
            "name": name,
            "description": description,
            "tags": existing_tags,
            "project_id": project_id,
        })
        count += 1
    return receipt("ok", "reindex", f"{count} skills indexed")


def cmd_history(skill_id: str) -> dict:
    if not skill_id:
        return error_receipt("Skill ID required", "history")
    from src.shared import is_safe_skill_id
    if not is_safe_skill_id(skill_id):
        return error_receipt(f"Invalid skill ID: {skill_id}", "history")
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

    always_allowed = ("setup", "init", "skip", "start", "stop", "registry", "pause", "resume", "status", "skills", "reindex", "history", "overview", "dashboard", "scrape-transcript", "skill-write", "skill-meta")
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
            result = cmd_stop()
            print(json.dumps(result))

        elif command == "resume":
            result = cmd_start()
            print(json.dumps(result))

        elif command == "stop":
            result = cmd_stop()
            print(json.dumps(result))

        elif command == "start":
            result = cmd_start()
            print(json.dumps(result))

        elif command == "status":
            result = cmd_skills()
            print(json.dumps(result))

        elif command == "init":
            project_dir = sys.argv[2] if len(sys.argv) > 2 else None
            result = cmd_init(project_dir)
            print(json.dumps(result))

        elif command == "skip":
            project_dir = sys.argv[2] if len(sys.argv) > 2 else None
            result = cmd_skip(project_dir)
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
            result = cmd_skills()
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
        print(json.dumps(error_receipt(f"{type(e).__name__}: {e}", command)), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

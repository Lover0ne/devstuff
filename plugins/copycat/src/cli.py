#!/usr/bin/env python3
"""Copycat CLI — template registry and dashboard management.

Commands:
  registry   --add/--remove/--list   Registry CRUD operations
  list                               List all templates
  delete     <template-id>           Remove template from registry and disk
  dashboard  [--no-open]             Generate and open interactive HTML dashboard
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.shared import copycat_dir, templates_dir, receipt, error_receipt, now_iso
from src.registry import add_entry, remove_entry, list_entries


def cmd_list() -> dict:
    entries = list_entries()
    by_mode = {}
    for e in entries:
        mode = e.get("mode", "unknown")
        if mode not in by_mode:
            by_mode[mode] = []
        by_mode[mode].append({
            "id": e.get("id"),
            "name": e.get("name"),
            "source_skill": e.get("source_skill", ""),
            "mode": mode,
            "placeholder_count": e.get("placeholder_count", 0),
            "created": e.get("created", ""),
            "updated": e.get("updated", ""),
        })
    return {
        "total": len(entries),
        "by_mode": by_mode,
        "templates": [
            {
                "id": e.get("id"),
                "name": e.get("name"),
                "source_skill": e.get("source_skill", ""),
                "mode": e.get("mode", ""),
                "placeholder_count": e.get("placeholder_count", 0),
                "created": e.get("created", ""),
            }
            for e in entries
        ],
    }


def cmd_delete(template_id: str) -> dict:
    if not template_id or "/" in template_id or "\\" in template_id or ".." in template_id:
        return error_receipt(f"Invalid template ID: {template_id}", "delete")
    result = remove_entry(template_id)
    if result.get("error"):
        return result
    template_dir = templates_dir() / template_id
    if template_dir.exists() and template_dir.is_dir():
        import shutil
        shutil.rmtree(str(template_dir), ignore_errors=True)
    return receipt("ok", "deleted", str(template_dir))


def cmd_dashboard() -> dict:
    from src.dashboard import generate
    no_open = "--no-open" in sys.argv
    return generate(no_open=no_open)


def cmd_registry_add(entry_json: str) -> dict:
    try:
        entry = json.loads(entry_json)
    except json.JSONDecodeError as e:
        return error_receipt(f"Invalid JSON: {e}", "registry_add")
    return add_entry(entry)


def cmd_registry_remove(template_id: str) -> dict:
    if not template_id or "/" in template_id or "\\" in template_id or ".." in template_id:
        return error_receipt(f"Invalid template ID: {template_id}", "registry_remove")
    return remove_entry(template_id)


def cmd_registry_list() -> dict:
    return {"templates": list_entries(), "count": len(list_entries())}


def main():
    if len(sys.argv) < 2:
        print(json.dumps(error_receipt("No command provided", "cli")), file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "registry":
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
                    print(json.dumps(error_receipt("Template ID required", "registry_remove")), file=sys.stderr)
                    sys.exit(1)
                result = cmd_registry_remove(sys.argv[3])
                print(json.dumps(result))
            elif subcmd == "--list":
                result = cmd_registry_list()
                print(json.dumps(result))
            else:
                print(json.dumps(error_receipt(f"Unknown registry subcommand: {subcmd}", "registry")), file=sys.stderr)
                sys.exit(1)

        elif command == "list":
            result = cmd_list()
            print(json.dumps(result))

        elif command == "delete":
            if len(sys.argv) < 3:
                print(json.dumps(error_receipt("Template ID required", "delete")), file=sys.stderr)
                sys.exit(1)
            result = cmd_delete(sys.argv[2])
            print(json.dumps(result))

        elif command == "dashboard":
            result = cmd_dashboard()
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

"""E2E: full plugin lifecycle — hook activation, skill creation, registry,
versioning, enable/disable, project isolation, transcript scraping.

Each test is self-contained with zero inherited context, simulating
the real flow a user goes through with the plugin.
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def plugin_env(tmp_path, monkeypatch):
    """Simulate a fresh plugin install: no config, no registry, no marker."""
    from src import config, registry, shared, skill_ops

    st_dir = tmp_path / ".claude" / "skilltrace"
    sk_dir = tmp_path / ".claude" / "skills"
    ver_dir = st_dir / "versions"

    monkeypatch.setattr(shared, "skilltrace_dir", lambda: st_dir)
    monkeypatch.setattr(shared, "skills_dir", lambda: sk_dir)
    monkeypatch.setattr(config, "_config_path", lambda: st_dir / "config.json")
    monkeypatch.setattr(registry, "_registry_path", lambda: st_dir / "registry.json")
    monkeypatch.setattr(skill_ops, "_versions_dir", lambda: ver_dir)
    monkeypatch.setattr(skill_ops, "_skill_dir", lambda sid: sk_dir / sid)
    monkeypatch.setattr(skill_ops, "_skill_path", lambda sid: sk_dir / sid / "SKILL.md")
    monkeypatch.setattr(skill_ops, "_version_path", lambda sid, v: ver_dir / sid / f"v{v}.md")

    from src import cli
    monkeypatch.setattr(cli, "skilltrace_dir", lambda: st_dir)
    monkeypatch.setattr(cli, "skills_dir", lambda: sk_dir)

    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    return {
        "tmp": tmp_path,
        "st_dir": st_dir,
        "sk_dir": sk_dir,
        "ver_dir": ver_dir,
        "project_dir": project_dir,
    }


def _write_transcript(path, entries):
    path.write_text(
        "\n".join(json.dumps(e) for e in entries) + "\n",
        encoding="utf-8",
    )


class TestHookActivation:
    """Simulate SessionStart/UserPromptSubmit/SessionEnd hooks."""

    def test_session_start_first_run(self, plugin_env):
        """First-ever setup: welcome message + suggest init."""
        from src.cli import cmd_setup

        result = cmd_setup()
        assert result["status"] == "active"
        assert "Skilltrace installed" in result["additionalContext"]
        assert plugin_env["st_dir"].exists()
        assert plugin_env["sk_dir"].exists()

    def test_session_start_subsequent_no_marker(self, plugin_env):
        """Second run, no .skilltrace marker: suggest init."""
        from src.cli import cmd_setup

        cmd_setup()
        result = cmd_setup()
        assert result["additionalContext"] == "Skilltrace active."

    def test_session_start_with_marker(self, plugin_env, monkeypatch):
        """After init: just "Skilltrace active."."""
        from src.cli import cmd_setup, cmd_init
        from src import skill_ops

        monkeypatch.setattr(
            skill_ops, "find_or_create_project_id",
            lambda: ("proj-test", plugin_env["project_dir"] / ".skilltrace"),
        )
        cmd_setup()
        cmd_init()
        result = cmd_setup()
        assert result["additionalContext"] == "Skilltrace active."

    def test_reminder_hook(self, plugin_env):
        """UserPromptSubmit hook returns skilltracer instructions."""
        from src.cli import cmd_reminder

        result = cmd_reminder({"transcript_path": "/tmp/session.jsonl"})
        assert result == {}

    def test_finalize_hook(self, plugin_env):
        """SessionEnd hook returns skilltracer instructions."""
        from src.cli import cmd_finalize

        result = cmd_finalize({"transcript_path": "/tmp/session.jsonl"})
        assert "Session ending" in result["additionalContext"]
        assert "skilltracer" in result["additionalContext"]


class TestProjectInit:
    """Per-project opt-in via init command."""

    def test_init_creates_marker(self, plugin_env, monkeypatch):
        from src.cli import cmd_init
        from src import skill_ops, cli

        pid_val = ("proj-abc", plugin_env["project_dir"] / ".skilltrace")
        monkeypatch.setattr(skill_ops, "find_or_create_project_id", lambda: pid_val)
        monkeypatch.setattr(cli, "find_or_create_project_id", lambda: pid_val)
        result = cmd_init()
        assert result["status"] == "ok"
        assert result["action"] == "project_initialized"
        assert result["project_id"] == "proj-abc"

    def test_init_then_setup_shows_active(self, plugin_env, monkeypatch):
        from src.cli import cmd_setup, cmd_init
        from src import skill_ops

        marker_path = plugin_env["project_dir"] / ".skilltrace"
        monkeypatch.setattr(
            skill_ops, "find_or_create_project_id",
            lambda: ("proj-xyz", marker_path),
        )
        cmd_setup()
        cmd_init()
        marker_path.write_text(json.dumps({"project_id": "proj-xyz"}))

        result = cmd_setup()
        assert result["additionalContext"] == "Skilltrace active."


class TestSkillCreationAndVersioning:
    """Full skill lifecycle: create -> write -> version -> archive."""

    def test_create_skill(self, plugin_env, monkeypatch):
        from src.cli import cmd_setup, cmd_skill_write
        from src import skill_ops

        monkeypatch.setattr(
            skill_ops, "find_or_create_project_id",
            lambda: ("proj-test", plugin_env["project_dir"] / ".skilltrace"),
        )
        cmd_setup()

        result = cmd_skill_write(json.dumps({
            "action": "create",
            "name": "Building MCP Server for Stripe",
            "tags": ["mcp", "stripe", "fastmcp"],
        }))
        assert result["status"] == "ok"
        assert result["action"] == "create"
        assert result["version"] == 1
        assert result["skill_id"] == "building-mcp-server-for-stripe"
        assert Path(result["write_to"]).exists()

    def test_write_content_then_version(self, plugin_env, monkeypatch):
        from src.cli import cmd_setup, cmd_skill_write
        from src import skill_ops

        monkeypatch.setattr(
            skill_ops, "find_or_create_project_id",
            lambda: ("proj-test", plugin_env["project_dir"] / ".skilltrace"),
        )
        cmd_setup()

        r1 = cmd_skill_write(json.dumps({
            "action": "create",
            "name": "Auth Setup with Clerk",
            "tags": ["auth", "clerk"],
        }))
        skill_id = r1["skill_id"]
        Path(r1["write_to"]).write_text(
            "---\nname: auth-setup-clerk\ndescription: \"Use when setting up Clerk auth\"\n---\n# Auth v1",
            encoding="utf-8",
        )

        r2 = cmd_skill_write(json.dumps({
            "action": "new_version",
            "id": skill_id,
            "change_summary": "Added refresh token handling",
        }))
        assert r2["status"] == "ok"
        assert r2["version"] == 2
        archived = Path(r2["archived"])
        assert archived.exists()
        assert "Auth v1" in archived.read_text(encoding="utf-8")
        assert "<!-- SKILL_BODY -->" in Path(r2["write_to"]).read_text(encoding="utf-8")

    def test_three_versions_all_archived(self, plugin_env, monkeypatch):
        from src.cli import cmd_setup, cmd_skill_write, cmd_registry_list
        from src import skill_ops

        monkeypatch.setattr(
            skill_ops, "find_or_create_project_id",
            lambda: ("proj-test", plugin_env["project_dir"] / ".skilltrace"),
        )
        cmd_setup()

        r1 = cmd_skill_write(json.dumps({
            "action": "create",
            "name": "Deploy Pipeline",
            "tags": ["ci"],
        }))
        sid = r1["skill_id"]
        Path(r1["write_to"]).write_text("# v1", encoding="utf-8")

        r2 = cmd_skill_write(json.dumps({
            "action": "new_version",
            "id": sid,
            "change_summary": "Added staging",
        }))
        Path(r2["write_to"]).write_text("# v2", encoding="utf-8")

        r3 = cmd_skill_write(json.dumps({
            "action": "new_version",
            "id": sid,
            "change_summary": "Added rollback",
        }))

        assert r3["version"] == 3
        assert "# v1" in Path(r2["archived"]).read_text(encoding="utf-8")
        assert "# v2" in Path(r3["archived"]).read_text(encoding="utf-8")

        entries = cmd_registry_list()
        matching = [e for e in entries if e["id"] == sid]
        assert len(matching) == 1
        assert matching[0]["version"] == 3


class TestRegistryOperations:
    """Registry CRUD and project filtering."""

    def test_add_list_remove(self, plugin_env):
        from src.cli import cmd_setup, cmd_registry_add, cmd_registry_list, cmd_registry_remove

        cmd_setup()

        cmd_registry_add(json.dumps({
            "id": "sk-test",
            "name": "Test Skill",
            "tags": ["test"],
            "path": "sk-test/SKILL.md",
        }))
        entries = cmd_registry_list()
        assert len(entries) == 1
        assert entries[0]["name"] == "Test Skill"

        cmd_registry_remove("sk-test")
        assert len(cmd_registry_list()) == 0

    def test_project_filtering(self, plugin_env, monkeypatch):
        from src.cli import cmd_setup, cmd_skill_write, cmd_registry_list
        from src import skill_ops

        cmd_setup()

        monkeypatch.setattr(
            skill_ops, "find_or_create_project_id",
            lambda: ("proj-A", plugin_env["project_dir"] / ".skilltrace"),
        )
        cmd_skill_write(json.dumps({
            "action": "create",
            "name": "Skill from Project A",
            "tags": ["a"],
        }))

        monkeypatch.setattr(
            skill_ops, "find_or_create_project_id",
            lambda: ("proj-B", plugin_env["project_dir"] / ".other"),
        )
        cmd_skill_write(json.dumps({
            "action": "create",
            "name": "Skill from Project B",
            "tags": ["b"],
        }))

        all_entries = cmd_registry_list(project_only=False)
        assert len(all_entries) == 2

        (plugin_env["project_dir"] / ".skilltrace").write_text(
            json.dumps({"project_id": "proj-A"})
        )
        filtered = cmd_registry_list(project_only=True)
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Skill from Project A"


class TestSkillsInventory:
    """cmd_skills returns structured inventory with descriptions."""

    def test_empty_inventory(self, plugin_env):
        from src.cli import cmd_setup, cmd_skills

        cmd_setup()
        result = cmd_skills()
        assert result["total"] == 0
        assert result["skills"] == []

    def test_inventory_with_description(self, plugin_env, monkeypatch):
        from src.cli import cmd_setup, cmd_skill_write, cmd_skills
        from src import skill_ops

        monkeypatch.setattr(
            skill_ops, "find_or_create_project_id",
            lambda: ("proj-inv", plugin_env["project_dir"] / ".skilltrace"),
        )
        cmd_setup()

        r = cmd_skill_write(json.dumps({
            "action": "create",
            "name": "MCP Stripe Server",
            "description": "Use when building MCP server for Stripe API",
            "tags": ["mcp", "stripe"],
        }))
        Path(r["write_to"]).write_text(
            '---\nname: mcp-stripe-server\ndescription: "Use when building MCP server for Stripe API"\n---\n# MCP Stripe Server',
            encoding="utf-8",
        )

        (plugin_env["project_dir"] / ".skilltrace").write_text(
            json.dumps({"project_id": "proj-inv"})
        )
        result = cmd_skills()
        assert result["total"] == 1
        assert result["this_project"] == 1
        assert result["skills"][0]["description"] == "Use when building MCP server for Stripe API"


class TestEnableDisable:
    """Plugin pause/resume and disabled-state behavior."""

    def test_pause_disables(self, plugin_env):
        from src.cli import cmd_setup, cmd_pause, cmd_status

        cmd_setup()
        cmd_pause()
        status = cmd_status()
        assert status["enabled"] is False

    def test_resume_enables(self, plugin_env):
        from src.cli import cmd_setup, cmd_pause, cmd_resume, cmd_status

        cmd_setup()
        cmd_pause()
        cmd_resume()
        status = cmd_status()
        assert status["enabled"] is True

    def test_disabled_allows_always_allowed(self, plugin_env):
        """setup/init/registry/pause/resume/status/skills work when disabled."""
        from src.cli import cmd_setup, cmd_pause, cmd_status, cmd_skills

        cmd_setup()
        cmd_pause()
        status = cmd_status()
        assert status["enabled"] is False
        result = cmd_skills()
        assert "total" in result
        result2 = cmd_setup()
        assert result2["status"] in ("active", "dormant")


class TestTranscriptScraping:
    """Transcript scraping through CLI interface."""

    def test_scrape_user_and_assistant(self, plugin_env):
        from src.cli import cmd_setup, cmd_scrape_transcript

        cmd_setup()
        t = plugin_env["project_dir"] / "transcript.jsonl"
        _write_transcript(t, [
            {"type": "user", "message": {"role": "user", "content": "build MCP server"}},
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Creating server..."},
                        {"type": "tool_use", "name": "Write", "input": {"file_path": "server.py"}},
                    ],
                },
            },
        ])
        result = cmd_scrape_transcript(str(t))
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert any(t["tool"] == "Write" for t in result[1].get("tools", []))

    def test_scrape_empty_file(self, plugin_env):
        from src.cli import cmd_scrape_transcript

        t = plugin_env["project_dir"] / "empty.jsonl"
        t.write_text("", encoding="utf-8")
        result = cmd_scrape_transcript(str(t))
        assert result == []


class TestReindex:
    """Reindex rebuilds registry from SKILL.md files on disk."""

    def test_reindex_picks_up_skill_files(self, plugin_env):
        from src.cli import cmd_setup, cmd_reindex, cmd_registry_list

        cmd_setup()

        skill_dir = plugin_env["sk_dir"] / "sk-manual"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "# Manual Skill\nSome content.",
            encoding="utf-8",
        )

        result = cmd_reindex()
        assert result["status"] == "ok"
        assert "1 skills indexed" in result["file"]

        entries = cmd_registry_list()
        assert len(entries) == 1
        assert entries[0]["id"] == "sk-manual"
        assert entries[0]["name"] == "Manual Skill"


class TestErrorHandling:
    """Invalid inputs return clean errors."""

    def test_create_missing_name(self, plugin_env):
        from src.cli import cmd_setup, cmd_skill_write

        cmd_setup()
        result = cmd_skill_write(json.dumps({"action": "create", "tags": ["test"]}))
        assert "error" in result

    def test_unknown_action(self, plugin_env):
        from src.cli import cmd_setup, cmd_skill_write

        cmd_setup()
        result = cmd_skill_write(json.dumps({"action": "delete"}))
        assert "error" in result

    def test_version_nonexistent_skill(self, plugin_env):
        from src.cli import cmd_setup, cmd_skill_write

        cmd_setup()
        result = cmd_skill_write(json.dumps({
            "action": "new_version",
            "id": "sk-nope",
        }))
        assert "error" in result

    def test_invalid_json_registry(self, plugin_env):
        from src.cli import cmd_setup, cmd_registry_add

        cmd_setup()
        result = cmd_registry_add("not-json")
        assert "error" in result


class TestFullLifecycleE2E:
    """Complete end-to-end: install -> init -> create skill -> version -> list -> disable -> re-enable."""

    def test_complete_flow(self, plugin_env, monkeypatch):
        from src.cli import (
            cmd_setup, cmd_init, cmd_skill_write, cmd_skills,
            cmd_pause, cmd_resume, cmd_status, cmd_registry_list,
        )
        from src import skill_ops, cli

        pid_val = ("proj-e2e", plugin_env["project_dir"] / ".skilltrace")
        monkeypatch.setattr(skill_ops, "find_or_create_project_id", lambda: pid_val)
        monkeypatch.setattr(cli, "find_or_create_project_id", lambda: pid_val)

        # 1. First-run setup (SessionStart hook)
        r = cmd_setup()
        assert r["status"] == "active"
        assert "Skilltrace installed" in r["additionalContext"]

        # 2. Init project
        r = cmd_init()
        assert r["status"] == "ok"
        assert r["project_id"] == "proj-e2e"

        # 3. Write marker so subsequent reads find it
        (plugin_env["project_dir"] / ".skilltrace").write_text(
            json.dumps({"project_id": "proj-e2e"})
        )

        # 4. Subsequent setup shows active
        r = cmd_setup()
        assert r["additionalContext"] == "Skilltrace active."

        # 5. Create first skill
        r1 = cmd_skill_write(json.dumps({
            "action": "create",
            "name": "Setting Up NextJS Auth with Clerk and Drizzle",
            "description": "Use when setting up NextJS auth with Clerk and Drizzle ORM",
            "tags": ["nextjs", "clerk", "drizzle", "auth"],
        }))
        assert r1["version"] == 1
        sid = r1["skill_id"]

        Path(r1["write_to"]).write_text(
            '---\nname: nextjs-auth-clerk-drizzle\n'
            'description: "Use when setting up NextJS auth with Clerk and Drizzle ORM"\n'
            '---\n# NextJS Auth with Clerk and Drizzle\n## What\nAuth setup steps.',
            encoding="utf-8",
        )

        # 6. Skills inventory shows 1 skill
        inv = cmd_skills()
        assert inv["total"] == 1
        assert inv["this_project"] == 1
        assert inv["skills"][0]["description"] == "Use when setting up NextJS auth with Clerk and Drizzle ORM"

        # 7. Version the skill
        r2 = cmd_skill_write(json.dumps({
            "action": "new_version",
            "id": sid,
            "change_summary": "Added social login providers",
        }))
        assert r2["version"] == 2
        archived = Path(r2["archived"])
        assert archived.exists()
        assert "Auth setup steps" in archived.read_text(encoding="utf-8")

        # 8. Registry shows version 2
        entries = cmd_registry_list()
        match = [e for e in entries if e["id"] == sid]
        assert match[0]["version"] == 2
        assert match[0]["change_summary"] == "Added social login providers"

        # 9. Pause plugin
        cmd_pause()
        st = cmd_status()
        assert st["enabled"] is False

        # 10. Skills still accessible when paused
        inv2 = cmd_skills()
        assert inv2["total"] == 1

        # 11. Resume
        cmd_resume()
        st = cmd_status()
        assert st["enabled"] is True

        # 12. Status shows correct counts
        assert st["total_skills"] == 1
        assert st["project_skills"] == 1
        assert st["project_id"] == "proj-e2e"

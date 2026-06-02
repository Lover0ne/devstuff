import json
from pathlib import Path

import pytest


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    from src import config, registry, shared, skill_ops

    sf_dir = tmp_path / ".claude" / "skillforge"
    sk_dir = tmp_path / ".claude" / "skills"
    ver_dir = sf_dir / "versions"

    monkeypatch.setattr(shared, "skillforge_dir", lambda: sf_dir)
    monkeypatch.setattr(shared, "skills_dir", lambda: sk_dir)
    monkeypatch.setattr(config, "_config_path", lambda: sf_dir / "config.json")
    monkeypatch.setattr(registry, "_registry_path", lambda: sf_dir / "registry.json")
    monkeypatch.setattr(registry, "_lock_path", lambda: sf_dir / "registry.lock")
    monkeypatch.setattr(skill_ops, "_versions_dir", lambda: ver_dir)
    monkeypatch.setattr(skill_ops, "_skill_dir", lambda sid: sk_dir / sid)
    monkeypatch.setattr(skill_ops, "_skill_path", lambda sid: sk_dir / sid / "SKILL.md")
    monkeypatch.setattr(skill_ops, "_version_path", lambda sid, v: ver_dir / sid / f"v{v}.md")

    from src import cli
    monkeypatch.setattr(cli, "skillforge_dir", lambda: sf_dir)
    monkeypatch.setattr(cli, "skills_dir", lambda: sk_dir)

    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestSetup:
    def test_setup_creates_dirs(self, cli_env):
        from src.cli import cmd_setup
        result = cmd_setup()
        assert result["status"] == "ok"
        assert "Skillforge ready" in result["additionalContext"]
        assert "skillforge-launch" in result["additionalContext"]


class TestSkillWrite:
    def test_create_returns_scaffold(self, cli_env):
        from src.cli import cmd_skill_write
        result = cmd_skill_write(json.dumps({"action": "create", "name": "Test Skill"}))
        assert result["status"] == "ok"
        assert result["skill_id"] == "test-skill"
        assert "instructions" in result
        path = Path(result["write_to"])
        assert "<!-- SKILL_BODY -->" in path.read_text()

    def test_create_then_meta(self, cli_env):
        from src.cli import cmd_skill_write
        from src.skill_ops import update_skill_meta
        from src.registry import list_entries
        r = cmd_skill_write(json.dumps({"action": "create", "name": "Full Flow"}))
        path = Path(r["write_to"])
        path.write_text('---\nname: full-flow\ndescription: "test"\n---\n\n# Body')
        meta = update_skill_meta(r["skill_id"], "Use when testing", ["test"])
        assert meta["status"] == "ok"
        entries = list_entries()
        assert entries[0]["description"] == "Use when testing"

    def test_invalid_json(self, cli_env):
        from src.cli import cmd_skill_write
        result = cmd_skill_write("not json")
        assert "error" in result

    def test_unknown_action(self, cli_env):
        from src.cli import cmd_skill_write
        result = cmd_skill_write(json.dumps({"action": "delete"}))
        assert "error" in result


class TestStatus:
    def test_status_returns_counts(self, cli_env):
        from src.cli import cmd_setup, cmd_status, cmd_skill_write
        cmd_setup()
        cmd_skill_write(json.dumps({"action": "create", "name": "Skill 1"}))
        result = cmd_status()
        assert result["total_skills"] == 1

"""End-to-end tests: full skill lifecycle through CLI commands."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def full_env(tmp_path, monkeypatch):
    from src import config, registry, shared, skill_ops

    config_file = tmp_path / "config.json"
    cfg = config.default_config()
    cfg["registry"] = str(tmp_path / "registry.json")
    cfg["skills_dir"] = str(tmp_path / "skills")
    cfg["versions_dir"] = str(tmp_path / "versions")
    config_file.write_text(json.dumps(cfg))

    monkeypatch.setattr(config, "_config_path", lambda: config_file)
    monkeypatch.setattr(registry, "_registry_path", lambda: tmp_path / "registry.json")
    monkeypatch.setattr(shared, "skills_dir", lambda: tmp_path / "skills")
    monkeypatch.setattr(shared, "skilltrace_dir", lambda: tmp_path / "skilltrace")
    monkeypatch.setattr(skill_ops, "_versions_dir", lambda: tmp_path / "versions")
    monkeypatch.setattr(skill_ops, "_skill_dir", lambda sid: tmp_path / "skills" / sid)
    monkeypatch.setattr(skill_ops, "_skill_path", lambda sid: tmp_path / "skills" / sid / "SKILL.md")
    monkeypatch.setattr(skill_ops, "_version_path", lambda sid, v: tmp_path / "versions" / sid / f"v{v}.md")
    monkeypatch.setattr(skill_ops, "find_or_create_project_id", lambda: ("proj-e2etest", tmp_path / ".skilltrace"))
    return tmp_path


def test_create_via_cli_then_list(full_env):
    """CLI skill-write create -> registry list returns new entry."""
    from src.cli import cmd_skill_write, cmd_registry_list

    result = cmd_skill_write(json.dumps({
        "action": "create",
        "name": "Docker Compose Setup",
        "tags": ["docker", "infra"],
    }))
    assert result["status"] == "ok"
    assert result["action"] == "create"
    assert result["version"] == 1

    entries = cmd_registry_list()
    assert len(entries) == 1
    assert entries[0]["name"] == "Docker Compose Setup"
    assert entries[0]["project_id"] == "proj-e2etest"


def test_create_then_new_version_via_cli(full_env):
    """CLI create -> write content -> new_version -> old archived."""
    from src.cli import cmd_skill_write

    r1 = cmd_skill_write(json.dumps({
        "action": "create",
        "name": "API Auth",
        "tags": ["auth", "api"],
    }))
    skill_id = r1["skill_id"]
    Path(r1["write_to"]).write_text("# API Auth v1\nJWT setup steps.", encoding="utf-8")

    r2 = cmd_skill_write(json.dumps({
        "action": "new_version",
        "id": skill_id,
        "change_summary": "Added refresh token flow",
    }))
    assert r2["status"] == "ok"
    assert r2["version"] == 2
    archived = Path(r2["archived"])
    assert archived.exists()
    assert "JWT setup steps" in archived.read_text(encoding="utf-8")
    assert Path(r2["write_to"]).read_text(encoding="utf-8") == ""


def test_project_filtered_list(full_env, monkeypatch):
    """--project flag filters to current project only."""
    from src import skill_ops
    from src.cli import cmd_skill_write, cmd_registry_list

    cmd_skill_write(json.dumps({
        "action": "create",
        "name": "Skill A",
        "tags": ["a"],
    }))

    monkeypatch.setattr(skill_ops, "find_or_create_project_id", lambda: ("proj-other", full_env / ".other"))

    cmd_skill_write(json.dumps({
        "action": "create",
        "name": "Skill B",
        "tags": ["b"],
    }))

    all_entries = cmd_registry_list(project_only=False)
    assert len(all_entries) == 2

    (full_env / ".skilltrace").write_text(json.dumps({"project_id": "proj-e2etest"}))
    monkeypatch.chdir(full_env)
    filtered = cmd_registry_list(project_only=True)
    assert len(filtered) == 1
    assert filtered[0]["name"] == "Skill A"


def test_skill_write_invalid_action(full_env):
    """Unknown action returns error."""
    from src.cli import cmd_skill_write

    result = cmd_skill_write(json.dumps({"action": "delete"}))
    assert "error" in result


def test_skill_write_missing_name(full_env):
    """Create without name returns error."""
    from src.cli import cmd_skill_write

    result = cmd_skill_write(json.dumps({"action": "create", "tags": ["test"]}))
    assert "error" in result


def test_new_version_nonexistent_skill(full_env):
    """New version on missing skill returns error."""
    from src.cli import cmd_skill_write

    result = cmd_skill_write(json.dumps({
        "action": "new_version",
        "id": "sk-doesnotexist",
    }))
    assert "error" in result


def test_full_lifecycle_three_versions(full_env):
    """Create -> v2 -> v3, verify all archives exist and registry is correct."""
    from src.cli import cmd_skill_write, cmd_registry_list

    r1 = cmd_skill_write(json.dumps({
        "action": "create",
        "name": "Deployment Pipeline",
        "tags": ["ci", "deploy"],
    }))
    sid = r1["skill_id"]
    Path(r1["write_to"]).write_text("# v1 content", encoding="utf-8")

    r2 = cmd_skill_write(json.dumps({
        "action": "new_version",
        "id": sid,
        "change_summary": "Added staging env",
    }))
    Path(r2["write_to"]).write_text("# v2 content", encoding="utf-8")

    r3 = cmd_skill_write(json.dumps({
        "action": "new_version",
        "id": sid,
        "change_summary": "Added rollback",
    }))

    assert r3["version"] == 3
    assert Path(r2["archived"]).read_text(encoding="utf-8") == "# v1 content"
    assert Path(r3["archived"]).read_text(encoding="utf-8") == "# v2 content"

    entries = cmd_registry_list()
    assert len(entries) == 1
    assert entries[0]["version"] == 3
    assert entries[0]["change_summary"] == "Added rollback"

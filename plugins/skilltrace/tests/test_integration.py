"""Integration tests: v3 pipeline — setup, registry, transcript scraping."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def skilltrace_env(tmp_path, monkeypatch):
    from src import config, registry
    config_file = tmp_path / "config.json"
    cfg = config.default_config()
    cfg["registry"] = str(tmp_path / "registry.json")
    cfg["skills_dir"] = str(tmp_path / "skills")
    cfg["versions_dir"] = str(tmp_path / "versions")
    config_file.write_text(json.dumps(cfg))
    monkeypatch.setattr(config, "_config_path", lambda: config_file)
    monkeypatch.setattr(registry, "_registry_path", lambda: Path(cfg["registry"]))
    return tmp_path


def test_setup_returns_active_with_marker(skilltrace_env, monkeypatch):
    from src import cli, shared, config
    st_dir = skilltrace_env / "skilltrace"
    st_dir.mkdir(parents=True, exist_ok=True)
    (st_dir / "config.json").write_text(json.dumps({"enabled": True}))
    monkeypatch.setattr(shared, "skilltrace_dir", lambda: st_dir)
    monkeypatch.setattr(shared, "skills_dir", lambda: skilltrace_env / "skills")
    monkeypatch.setattr(config, "_config_path", lambda: st_dir / "config.json")
    (skilltrace_env / ".skilltrace").write_text(json.dumps({"project_id": "proj-int"}))
    monkeypatch.chdir(skilltrace_env)
    result = cli.cmd_setup()
    assert result["status"] == "active"
    assert result["additionalContext"] == "Skilltrace active."


def test_registry_round_trip(skilltrace_env):
    from src.registry import add_entry, remove_entry, list_entries

    add_entry({
        "id": "test-skill",
        "name": "Test Skill",
        "tags": ["test"],
        "files_touched": ["test.py"],
        "tools_used": ["Write"],
        "path": "test-skill/SKILL.md",
    })
    entries = list_entries()
    assert len(entries) == 1
    assert entries[0]["version"] == 1

    add_entry({
        "id": "test-skill",
        "name": "Test Skill Updated",
        "tags": ["test", "updated"],
        "path": "test-skill/SKILL.md",
    })
    entries = list_entries()
    assert len(entries) == 1
    assert entries[0]["version"] == 2

    remove_entry("test-skill")
    assert len(list_entries()) == 0


def test_disabled_plugin(skilltrace_env):
    from src.config import set_enabled, is_enabled
    set_enabled(False)
    assert is_enabled() is False
    set_enabled(True)
    assert is_enabled() is True

import json
from pathlib import Path

import pytest


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    from src import config
    config_file = tmp_path / "config.json"
    cfg = config.default_config()
    cfg["registry"] = str(tmp_path / "registry.json")
    config_file.write_text(json.dumps(cfg))
    monkeypatch.setattr(config, "_config_path", lambda: config_file)
    return tmp_path


def _write_transcript(path, entries):
    path.write_text(
        "\n".join(json.dumps(e) for e in entries) + "\n",
        encoding="utf-8",
    )


def test_setup_first_run_welcome(tmp_path, monkeypatch):
    from src import cli, shared, config
    st_dir = tmp_path / "skilltrace"
    monkeypatch.setattr(shared, "skilltrace_dir", lambda: st_dir)
    monkeypatch.setattr(shared, "skills_dir", lambda: tmp_path / "skills")
    monkeypatch.setattr(cli, "skilltrace_dir", lambda: st_dir)
    monkeypatch.setattr(cli, "skills_dir", lambda: tmp_path / "skills")
    monkeypatch.setattr(config, "_config_path", lambda: st_dir / "config.json")
    monkeypatch.chdir(tmp_path)
    result = cli.cmd_setup()
    assert result["status"] == "active"
    assert "Skilltrace installed" in result["additionalContext"]
    assert "skilltrace:pause" in result["additionalContext"]


def test_setup_with_marker_active(tmp_path, monkeypatch):
    from src import cli, shared, config
    st_dir = tmp_path / "skilltrace"
    st_dir.mkdir(parents=True)
    (st_dir / "config.json").write_text(json.dumps({"enabled": True}))
    monkeypatch.setattr(shared, "skilltrace_dir", lambda: st_dir)
    monkeypatch.setattr(shared, "skills_dir", lambda: tmp_path / "skills")
    monkeypatch.setattr(config, "_config_path", lambda: st_dir / "config.json")
    (tmp_path / ".skilltrace").write_text(json.dumps({"project_id": "proj-test"}))
    monkeypatch.chdir(tmp_path)
    result = cli.cmd_setup()
    assert result["additionalContext"] == "Skilltrace active."


def test_setup_no_marker_suggests_init(tmp_path, monkeypatch):
    from src import cli, shared, config
    st_dir = tmp_path / "skilltrace"
    st_dir.mkdir(parents=True)
    (st_dir / "config.json").write_text(json.dumps({"enabled": True}))
    monkeypatch.setattr(shared, "skilltrace_dir", lambda: st_dir)
    monkeypatch.setattr(shared, "skills_dir", lambda: tmp_path / "skills")
    monkeypatch.setattr(config, "_config_path", lambda: st_dir / "config.json")
    monkeypatch.chdir(tmp_path)
    result = cli.cmd_setup()
    assert result["additionalContext"] == "Skilltrace active."


def test_init_creates_marker(tmp_path, monkeypatch):
    from src import cli, shared
    monkeypatch.setattr(shared, "skilltrace_dir", lambda: tmp_path / "skilltrace")
    monkeypatch.setattr(shared, "skills_dir", lambda: tmp_path / "skills")
    monkeypatch.chdir(tmp_path)
    result = cli.cmd_init()
    assert result["status"] == "ok"
    assert result["action"] == "project_initialized"
    assert (tmp_path / ".skilltrace").exists()
    marker_data = json.loads((tmp_path / ".skilltrace").read_text())
    assert marker_data["project_id"] == result["project_id"]


def test_skills_returns_inventory(tmp_path, monkeypatch):
    from src import cli, shared, registry
    monkeypatch.setattr(shared, "skilltrace_dir", lambda: tmp_path / "skilltrace")
    monkeypatch.setattr(shared, "skills_dir", lambda: tmp_path / "skills")
    reg_file = tmp_path / "skilltrace" / "registry.json"
    reg_file.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(registry, "_registry_path", lambda: reg_file)
    registry.add_entry({"id": "sk-001", "name": "Test Skill", "tags": [], "path": "sk-001/SKILL.md", "project_id": "proj-abc"})
    monkeypatch.chdir(tmp_path)
    result = cli.cmd_skills()
    assert result["total"] == 1
    assert len(result["skills"]) == 1
    assert result["skills"][0]["name"] == "Test Skill"


def test_scrape_transcript_via_cli(cli_env):
    from src import cli
    t = cli_env / "t.jsonl"
    _write_transcript(t, [
        {"type": "user", "message": {"role": "user", "content": "hello"}},
    ])
    result = cli.cmd_scrape_transcript(str(t))
    assert len(result) == 1
    assert result[0]["role"] == "user"


def test_registry_add_via_cli(cli_env, monkeypatch):
    from src import cli, registry
    reg_file = cli_env / "registry.json"
    monkeypatch.setattr(registry, "_registry_path", lambda: reg_file)
    entry = {"id": "test-skill", "name": "Test", "tags": ["test"], "path": "test/SKILL.md"}
    result = cli.cmd_registry_add(json.dumps(entry))
    assert result["status"] == "ok"


def test_registry_list_via_cli(cli_env, monkeypatch):
    from src import cli, registry
    reg_file = cli_env / "registry.json"
    monkeypatch.setattr(registry, "_registry_path", lambda: reg_file)
    registry.add_entry({"id": "a", "name": "A", "tags": [], "path": "a/SKILL.md"})
    result = cli.cmd_registry_list()
    assert isinstance(result, dict)
    entries = result["skills"]
    assert len(entries) == 1


def test_reminder_returns_empty_without_marker(cli_env):
    from src.cli import cmd_reminder
    result = cmd_reminder({"transcript_path": "/tmp/t.jsonl"})
    assert result == {}


def test_finalize_returns_additional_context(cli_env):
    from src.cli import cmd_finalize
    result = cmd_finalize({"transcript_path": "/tmp/t.jsonl"})
    assert "additionalContext" in result
    assert "skilltracer" in result["additionalContext"]
    assert "Session ending" in result["additionalContext"]

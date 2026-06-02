"""Tests for skill_ops — deterministic scaffold, archive, versioning."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def skill_env(tmp_path, monkeypatch):
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
    monkeypatch.setattr(skill_ops, "find_or_create_project_id", lambda: ("proj-test1234", tmp_path / ".skilltrace"))
    return tmp_path


class TestPrepareCreate:
    def test_creates_skill_dir_and_empty_file(self, skill_env):
        from src.skill_ops import prepare_create
        result = prepare_create({"name": "JWT Auth", "tags": ["auth"]})
        assert result["status"] == "ok"
        assert result["action"] == "create"
        assert result["version"] == 1
        assert result["skill_id"] == "jwt-auth"
        path = Path(result["write_to"])
        assert path.exists()
        content = path.read_text()
        assert "<!-- SKILL_BODY -->" in content
        assert "name: jwt-auth" in content

    def test_registers_with_project_id(self, skill_env):
        from src.skill_ops import prepare_create
        from src.registry import list_entries
        prepare_create({"name": "JWT Auth", "tags": ["auth"]})
        entries = list_entries()
        assert len(entries) == 1
        assert entries[0]["project_id"] == "proj-test1234"
        assert entries[0]["version"] == 1
        assert entries[0]["id"] == "jwt-auth"

    def test_generates_unique_ids(self, skill_env):
        from src.skill_ops import prepare_create
        r1 = prepare_create({"name": "Skill A", "tags": []})
        r2 = prepare_create({"name": "Skill B", "tags": []})
        assert r1["skill_id"] != r2["skill_id"]

    def test_rejects_missing_name(self, skill_env):
        from src.skill_ops import prepare_create
        result = prepare_create({"tags": ["test"]})
        assert "error" in result


class TestPrepareNewVersion:
    def test_archives_and_increments(self, skill_env):
        from src.skill_ops import prepare_create, prepare_new_version, _skill_path
        r = prepare_create({"name": "JWT Auth", "tags": ["auth"]})
        skill_id = r["skill_id"]
        _skill_path(skill_id).write_text("# Original content", encoding="utf-8")

        result = prepare_new_version(skill_id, "Fixed token expiry")
        assert result["status"] == "ok"
        assert result["action"] == "new_version"
        assert result["version"] == 2
        assert "archived" in result
        archived = Path(result["archived"])
        assert archived.exists()
        assert archived.read_text(encoding="utf-8") == "# Original content"
        assert archived.name == "v1.md"

    def test_consecutive_versions(self, skill_env):
        from src.skill_ops import prepare_create, prepare_new_version, _skill_path
        r = prepare_create({"name": "Test", "tags": []})
        sid = r["skill_id"]
        _skill_path(sid).write_text("v1", encoding="utf-8")
        r2 = prepare_new_version(sid)
        assert r2["version"] == 2
        _skill_path(sid).write_text("v2", encoding="utf-8")
        r3 = prepare_new_version(sid)
        assert r3["version"] == 3
        _skill_path(sid).write_text("v3", encoding="utf-8")
        r4 = prepare_new_version(sid, "Big refactor")
        assert r4["version"] == 4

    def test_stores_change_summary(self, skill_env):
        from src.skill_ops import prepare_create, prepare_new_version
        from src.registry import list_entries
        r = prepare_create({"name": "Test", "tags": []})
        prepare_new_version(r["skill_id"], "Added OAuth support")
        entries = list_entries()
        assert entries[0]["change_summary"] == "Added OAuth support"

    def test_rejects_nonexistent(self, skill_env):
        from src.skill_ops import prepare_new_version
        result = prepare_new_version("sk-nonexistent")
        assert "error" in result


class TestFullLifecycle:
    def test_create_then_multiple_versions(self, skill_env):
        from src.skill_ops import prepare_create, prepare_new_version, _skill_path, _version_path
        from src.registry import list_entries

        r = prepare_create({"name": "REST API", "tags": ["api"]})
        sid = r["skill_id"]
        _skill_path(sid).write_text("v1 content", encoding="utf-8")

        prepare_new_version(sid, "Added pagination")
        assert _version_path(sid, 1).exists()
        _skill_path(sid).write_text("v2 content", encoding="utf-8")

        prepare_new_version(sid, "Added caching")
        assert _version_path(sid, 2).exists()
        _skill_path(sid).write_text("v3 content", encoding="utf-8")

        prepare_new_version(sid, "Added GraphQL")
        assert _version_path(sid, 3).exists()

        entries = list_entries()
        assert len(entries) == 1
        assert entries[0]["version"] == 4
        assert entries[0]["change_summary"] == "Added GraphQL"


class TestProjectId:
    def test_find_existing(self, tmp_path):
        from src.shared import find_or_create_project_id
        marker = tmp_path / ".skilltrace"
        marker.write_text(json.dumps({"project_id": "proj-existing", "created": "2026-01-01T00:00:00Z"}))
        pid, path = find_or_create_project_id(tmp_path)
        assert pid == "proj-existing"
        assert path == marker

    def test_creates_new(self, tmp_path):
        from src.shared import find_or_create_project_id
        subdir = tmp_path / "deep" / "nested"
        subdir.mkdir(parents=True)
        pid, path = find_or_create_project_id(subdir)
        assert pid.startswith("proj-")
        assert path == subdir / ".skilltrace"
        assert path.exists()

    def test_does_not_walk_up(self, tmp_path):
        from src.shared import find_or_create_project_id
        marker = tmp_path / ".skilltrace"
        marker.write_text(json.dumps({"project_id": "proj-root", "created": "2026-01-01T00:00:00Z"}))
        subdir = tmp_path / "src" / "deep"
        subdir.mkdir(parents=True)
        pid, path = find_or_create_project_id(subdir)
        assert pid != "proj-root"
        assert path == subdir / ".skilltrace"

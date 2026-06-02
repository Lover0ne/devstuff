import json
from pathlib import Path

import pytest


@pytest.fixture
def skill_env(tmp_path, monkeypatch):
    from src import skill_ops, registry, shared, config

    sk_dir = tmp_path / ".claude" / "skills"
    sf_dir = tmp_path / ".claude" / "skillforge"
    ver_dir = sf_dir / "versions"

    monkeypatch.setattr(shared, "skills_dir", lambda: sk_dir)
    monkeypatch.setattr(shared, "skillforge_dir", lambda: sf_dir)
    monkeypatch.setattr(skill_ops, "_versions_dir", lambda: ver_dir)
    monkeypatch.setattr(skill_ops, "_skill_dir", lambda sid: sk_dir / sid)
    monkeypatch.setattr(skill_ops, "_skill_path", lambda sid: sk_dir / sid / "SKILL.md")
    monkeypatch.setattr(skill_ops, "_version_path", lambda sid, v: ver_dir / sid / f"v{v}.md")
    monkeypatch.setattr(registry, "_registry_path", lambda: sf_dir / "registry.json")
    monkeypatch.setattr(config, "_config_path", lambda: sf_dir / "config.json")
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestPrepareCreate:
    def test_creates_scaffold_with_marker(self, skill_env):
        from src.skill_ops import prepare_create
        result = prepare_create({"name": "Docker Deploy", "project_dir": str(skill_env)})
        assert result["status"] == "ok"
        assert result["action"] == "create"
        assert result["skill_id"] == "docker-deploy"
        path = Path(result["write_to"])
        assert path.exists()
        content = path.read_text()
        assert "<!-- SKILL_BODY -->" in content
        assert "name: docker-deploy" in content

    def test_returns_instructions(self, skill_env):
        from src.skill_ops import prepare_create
        result = prepare_create({"name": "Test Skill"})
        assert "instructions" in result
        assert "Edit" in result["instructions"]
        assert "SKILL_BODY" in result["instructions"]

    def test_collision_appends_uuid(self, skill_env):
        from src.skill_ops import prepare_create
        r1 = prepare_create({"name": "Deploy"})
        r2 = prepare_create({"name": "Deploy"})
        assert r1["skill_id"] != r2["skill_id"]
        assert r2["skill_id"].startswith("deploy-")

    def test_rejects_missing_name(self, skill_env):
        from src.skill_ops import prepare_create
        result = prepare_create({})
        assert "error" in result

    def test_version_history_created(self, skill_env):
        from src.skill_ops import prepare_create
        from src.registry import list_entries
        prepare_create({"name": "Test"})
        entries = list_entries()
        assert len(entries) == 1
        assert "version_history" in entries[0]
        assert entries[0]["version_history"][0]["version"] == 1

    def test_windows_reserved_name(self, skill_env):
        from src.skill_ops import _slugify
        assert _slugify("con") == "con-skill"
        assert _slugify("NUL") == "nul-skill"
        assert _slugify("normal") == "normal"


class TestPrepareNewVersion:
    def test_archives_and_increments(self, skill_env):
        from src.skill_ops import prepare_create, prepare_new_version
        r1 = prepare_create({"name": "Versioned"})
        Path(r1["write_to"]).write_text("---\nname: versioned\ndescription: \"test\"\n---\n\n# Content v1")
        r2 = prepare_new_version(r1["skill_id"], "Added feature")
        assert r2["version"] == 2
        assert r2["archived"] is not None
        assert Path(r2["archived"]).exists()

    def test_incomplete_file_not_archived(self, skill_env):
        from src.skill_ops import prepare_create, prepare_new_version
        r1 = prepare_create({"name": "Incomplete"})
        # Don't write body — marker still present
        r2 = prepare_new_version(r1["skill_id"])
        assert r2["version"] == 2
        assert "archived" not in r2 or r2.get("archived") is None

    def test_rejects_invalid_id(self, skill_env):
        from src.skill_ops import prepare_new_version
        result = prepare_new_version("../etc/passwd")
        assert "error" in result

    def test_rejects_nonexistent(self, skill_env):
        from src.skill_ops import prepare_new_version
        result = prepare_new_version("does-not-exist")
        assert "error" in result


class TestUpdateSkillMeta:
    def test_updates_registry_and_frontmatter(self, skill_env):
        from src.skill_ops import prepare_create, update_skill_meta
        from src.registry import list_entries
        r = prepare_create({"name": "Meta Test"})
        # Write body to pass marker check
        path = Path(r["write_to"])
        path.write_text('---\nname: meta-test\ndescription: "Use when [trigger]"\n---\n\n# Body content here')
        result = update_skill_meta(r["skill_id"], "Use when deploying", ["docker", "deploy"])
        assert result["status"] == "ok"
        assert result["instructions"] == "Metadata saved. Skill is complete."
        entries = list_entries()
        assert entries[0]["description"] == "Use when deploying"
        assert entries[0]["tags"] == ["docker", "deploy"]
        content = path.read_text()
        assert "Use when deploying" in content

    def test_rejects_if_body_not_written(self, skill_env):
        from src.skill_ops import prepare_create, update_skill_meta
        r = prepare_create({"name": "No Body"})
        result = update_skill_meta(r["skill_id"], "desc")
        assert "error" in result
        assert "Body not written" in result["error"]

    def test_rejects_invalid_id(self, skill_env):
        from src.skill_ops import update_skill_meta
        result = update_skill_meta("../../bad")
        assert "error" in result


class TestSanitization:
    def test_yaml_sanitization(self, skill_env):
        from src.skill_ops import _sanitize_yaml_string
        assert '\n' not in _sanitize_yaml_string("line1\nline2")
        assert '\\"' in _sanitize_yaml_string('has "quotes"')

    def test_idempotent(self, skill_env):
        from src.skill_ops import _sanitize_yaml_string
        original = 'Use when "deploying" apps'
        once = _sanitize_yaml_string(original)
        twice = _sanitize_yaml_string(once)
        assert once == twice

    def test_is_safe_id(self, skill_env):
        from src.skill_ops import _is_safe_id
        assert _is_safe_id("valid-id")
        assert _is_safe_id("abc123")
        assert not _is_safe_id("")
        assert not _is_safe_id("../bad")
        assert not _is_safe_id(".hidden")
        assert not _is_safe_id("C:\\path")

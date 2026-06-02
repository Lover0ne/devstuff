import json
from pathlib import Path

import pytest


@pytest.fixture
def reg_env(tmp_path, monkeypatch):
    from src import registry, shared, config

    sf_dir = tmp_path / ".claude" / "skillforge"
    monkeypatch.setattr(shared, "skillforge_dir", lambda: sf_dir)
    monkeypatch.setattr(registry, "_registry_path", lambda: sf_dir / "registry.json")
    monkeypatch.setattr(registry, "_lock_path", lambda: sf_dir / "registry.lock")
    monkeypatch.setattr(config, "_config_path", lambda: sf_dir / "config.json")
    return tmp_path


class TestRegistryCRUD:
    def test_add_and_list(self, reg_env):
        from src.registry import add_entry, list_entries
        add_entry({"id": "test-skill", "name": "Test"})
        entries = list_entries()
        assert len(entries) == 1
        assert entries[0]["id"] == "test-skill"

    def test_add_updates_existing(self, reg_env):
        from src.registry import add_entry, list_entries
        add_entry({"id": "skill-1", "name": "V1"})
        add_entry({"id": "skill-1", "name": "V2"})
        entries = list_entries()
        assert len(entries) == 1
        assert entries[0]["name"] == "V2"
        assert entries[0]["version"] == 2

    def test_remove(self, reg_env):
        from src.registry import add_entry, remove_entry, list_entries
        add_entry({"id": "to-remove", "name": "Bye"})
        remove_entry("to-remove")
        assert len(list_entries()) == 0

    def test_remove_nonexistent(self, reg_env):
        from src.registry import remove_entry
        result = remove_entry("nope")
        assert "error" in result


class TestRegistryValidation:
    def test_rejects_path_traversal_id(self, reg_env):
        from src.registry import add_entry
        result = add_entry({"id": "../etc/passwd", "name": "Bad"})
        assert "error" in result

    def test_rejects_dot_id(self, reg_env):
        from src.registry import add_entry
        result = add_entry({"id": ".hidden", "name": "Bad"})
        assert "error" in result

    def test_accepts_valid_id(self, reg_env):
        from src.registry import add_entry
        result = add_entry({"id": "valid-skill-123", "name": "Good"})
        assert result.get("status") == "ok"


class TestRegistryLock:
    def test_lock_creates_and_removes(self, reg_env):
        from src.registry import _registry_lock, _lock_path
        lock = _lock_path()
        with _registry_lock():
            assert lock.exists()
        assert not lock.exists()


class TestRegistryCorruption:
    def test_corrupted_json_recreates(self, reg_env):
        from src.registry import _registry_path, load_registry
        path = _registry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("NOT JSON", encoding="utf-8")
        reg = load_registry()
        assert reg["skills"] == []
        assert path.with_suffix(".json.old").exists()

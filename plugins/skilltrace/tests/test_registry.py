import json
from pathlib import Path

import pytest


def test_load_empty_registry(tmp_path, monkeypatch):
    from src import registry
    reg_file = tmp_path / "registry.json"
    monkeypatch.setattr(registry, "_registry_path", lambda: reg_file)
    data = registry.load_registry()
    assert data["version"] == 1
    assert data["skills"] == []


def test_load_existing_registry(tmp_path, monkeypatch):
    from src import registry
    reg_file = tmp_path / "registry.json"
    reg_data = {"version": 1, "skills": [{"id": "test-skill", "name": "Test"}]}
    reg_file.write_text(json.dumps(reg_data))
    monkeypatch.setattr(registry, "_registry_path", lambda: reg_file)
    data = registry.load_registry()
    assert len(data["skills"]) == 1


def test_add_skill_entry(tmp_path, monkeypatch):
    from src import registry
    reg_file = tmp_path / "registry.json"
    monkeypatch.setattr(registry, "_registry_path", lambda: reg_file)
    entry = {
        "id": "setup-mcp",
        "name": "Setting up MCP Server",
        "description": "Use when setting up MCP",
        "tags": ["mcp", "server"],
        "path": "setup-mcp/SKILL.md",
    }
    result = registry.add_entry(entry)
    assert result["status"] == "ok"
    data = registry.load_registry()
    assert len(data["skills"]) == 1
    assert data["skills"][0]["id"] == "setup-mcp"
    assert "created" in data["skills"][0]
    assert data["skills"][0]["version"] == 1


def test_add_duplicate_id_updates(tmp_path, monkeypatch):
    from src import registry
    reg_file = tmp_path / "registry.json"
    monkeypatch.setattr(registry, "_registry_path", lambda: reg_file)
    entry1 = {"id": "setup-mcp", "name": "V1", "tags": [], "path": "a/SKILL.md"}
    entry2 = {"id": "setup-mcp", "name": "V2", "tags": ["new"], "path": "a/SKILL.md"}
    registry.add_entry(entry1)
    registry.add_entry(entry2)
    data = registry.load_registry()
    assert len(data["skills"]) == 1
    assert data["skills"][0]["name"] == "V2"
    assert data["skills"][0]["version"] == 2


def test_remove_skill_entry(tmp_path, monkeypatch):
    from src import registry
    reg_file = tmp_path / "registry.json"
    monkeypatch.setattr(registry, "_registry_path", lambda: reg_file)
    registry.add_entry({"id": "to-remove", "name": "X", "tags": [], "path": "x/SKILL.md"})
    result = registry.remove_entry("to-remove")
    assert result["status"] == "ok"
    data = registry.load_registry()
    assert len(data["skills"]) == 0


def test_remove_nonexistent_returns_error(tmp_path, monkeypatch):
    from src import registry
    reg_file = tmp_path / "registry.json"
    monkeypatch.setattr(registry, "_registry_path", lambda: reg_file)
    result = registry.remove_entry("nope")
    assert "error" in result


def test_list_entries(tmp_path, monkeypatch):
    from src import registry
    reg_file = tmp_path / "registry.json"
    monkeypatch.setattr(registry, "_registry_path", lambda: reg_file)
    registry.add_entry({"id": "a", "name": "A", "tags": [], "path": "a/SKILL.md"})
    registry.add_entry({"id": "b", "name": "B", "tags": [], "path": "b/SKILL.md"})
    entries = registry.list_entries()
    assert len(entries) == 2


def test_corrupt_registry_rotates(tmp_path, monkeypatch):
    from src import registry
    reg_file = tmp_path / "registry.json"
    reg_file.write_text("NOT JSON {{{")
    monkeypatch.setattr(registry, "_registry_path", lambda: reg_file)
    data = registry.load_registry()
    assert data["version"] == 1
    assert (tmp_path / "registry.json.old").exists()

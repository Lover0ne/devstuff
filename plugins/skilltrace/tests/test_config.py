import json
from pathlib import Path

import pytest


def test_default_config_has_required_keys():
    from src.config import default_config
    cfg = default_config()
    assert cfg["enabled"] is True
    assert "registry" in cfg
    assert "skills_dir" in cfg
    assert "versions_dir" in cfg
    assert "boundary_threshold" not in cfg
    assert "content_truncate_chars" not in cfg


def test_load_config_creates_default_if_missing(tmp_path, monkeypatch):
    from src import config
    monkeypatch.setattr(config, "_config_path", lambda: tmp_path / "config.json")
    cfg = config.load_config()
    assert cfg["enabled"] is True
    assert (tmp_path / "config.json").exists()


def test_load_config_reads_existing(tmp_path, monkeypatch):
    from src import config
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"enabled": False, "skills_dir": "/custom/skills"}))
    monkeypatch.setattr(config, "_config_path", lambda: config_file)
    cfg = config.load_config()
    assert cfg["enabled"] is False
    assert cfg["skills_dir"] == "/custom/skills"


def test_load_config_fills_missing_keys(tmp_path, monkeypatch):
    from src import config
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"enabled": True}))
    monkeypatch.setattr(config, "_config_path", lambda: config_file)
    cfg = config.load_config()
    assert "skills_dir" in cfg
    assert "versions_dir" in cfg
    assert "registry" in cfg


def test_is_enabled_true(tmp_path, monkeypatch):
    from src import config
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"enabled": True}))
    monkeypatch.setattr(config, "_config_path", lambda: config_file)
    assert config.is_enabled() is True


def test_is_enabled_false(tmp_path, monkeypatch):
    from src import config
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"enabled": False}))
    monkeypatch.setattr(config, "_config_path", lambda: config_file)
    assert config.is_enabled() is False


def test_set_enabled(tmp_path, monkeypatch):
    from src import config
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"enabled": True}))
    monkeypatch.setattr(config, "_config_path", lambda: config_file)
    config.set_enabled(False)
    assert json.loads(config_file.read_text())["enabled"] is False



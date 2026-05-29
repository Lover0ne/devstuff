"""Configuration management for Skillforge."""

import json
from pathlib import Path

from src.shared import skillforge_dir, skills_dir, atomic_write_json


def _config_path() -> Path:
    return skillforge_dir() / "config.json"


def default_config() -> dict:
    return {
        "enabled": True,
        "skills_dir": str(skills_dir()),
        "versions_dir": str(skillforge_dir() / "versions"),
        "registry": str(skillforge_dir() / "registry.json"),
    }


def load_config() -> dict:
    path = _config_path()
    defaults = default_config()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, defaults)
        return defaults
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        atomic_write_json(path, defaults)
        return defaults
    merged = {**defaults, **stored}
    return merged


def is_enabled() -> bool:
    return load_config().get("enabled", True)


def set_enabled(value: bool) -> None:
    cfg = load_config()
    cfg["enabled"] = value
    atomic_write_json(_config_path(), cfg)

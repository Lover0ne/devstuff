import json
import os
import tempfile
from pathlib import Path

import pytest


def test_skilltrace_dir_returns_path():
    from src.shared import skilltrace_dir
    result = skilltrace_dir()
    assert isinstance(result, Path)
    assert str(result).endswith(".claude/skilltrace") or str(result).endswith(".claude\\skilltrace")


def test_skills_dir_returns_path():
    from src.shared import skills_dir
    result = skills_dir()
    assert isinstance(result, Path)
    assert str(result).endswith(".claude/skills") or str(result).endswith(".claude\\skills")



def test_atomic_write_json_creates_file(tmp_path):
    from src.shared import atomic_write_json
    target = tmp_path / "data.json"
    atomic_write_json(target, {"version": 1})
    data = json.loads(target.read_text())
    assert data["version"] == 1


def test_atomic_write_json_overwrites(tmp_path):
    from src.shared import atomic_write_json
    target = tmp_path / "data.json"
    atomic_write_json(target, {"version": 1})
    atomic_write_json(target, {"version": 2})
    data = json.loads(target.read_text())
    assert data["version"] == 2



def test_receipt_format():
    from src.shared import receipt
    r = receipt("ok", "test_action", "test.json")
    assert r["status"] == "ok"
    assert r["action"] == "test_action"
    assert r["file"] == "test.json"
    assert "ts" in r


def test_error_receipt_format():
    from src.shared import error_receipt
    r = error_receipt("something broke", "test_cmd")
    assert r["error"] == "something broke"
    assert r["command"] == "test_cmd"



def test_now_iso_format():
    from src.shared import now_iso
    ts = now_iso()
    assert "T" in ts
    assert ts.endswith("Z") or "+" in ts

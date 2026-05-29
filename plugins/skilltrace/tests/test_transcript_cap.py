"""Tests: _MAX_ENTRIES cap keeps the LAST 500 entries (most recent)."""

import json
from pathlib import Path

import pytest

from src.transcript import scrape_transcript, _MAX_ENTRIES


def _write_entries(path: Path, entries: list[dict]):
    path.write_text(
        "\n".join(json.dumps(e) for e in entries) + "\n",
        encoding="utf-8",
    )


def _make_user_entry(index: int) -> dict:
    return {
        "type": "user",
        "message": {"role": "user", "content": f"entry_{index}"},
    }


def _make_assistant_entry(index: int) -> dict:
    return {
        "type": "assistant",
        "message": {"content": [
            {"type": "text", "text": f"response_{index}"},
        ]},
    }


class TestMaxEntriesCap:
    TOTAL_ENTRIES = 700

    def test_returns_exactly_max_entries(self, tmp_path):
        f = tmp_path / "transcript.jsonl"
        entries = [_make_user_entry(i) for i in range(self.TOTAL_ENTRIES)]
        _write_entries(f, entries)
        result = scrape_transcript(str(f))
        assert len(result) == _MAX_ENTRIES

    def test_keeps_last_200_not_first_200(self, tmp_path):
        f = tmp_path / "transcript.jsonl"
        entries = [_make_user_entry(i) for i in range(self.TOTAL_ENTRIES)]
        _write_entries(f, entries)
        result = scrape_transcript(str(f))
        assert result[0]["text"] == "entry_200"
        assert result[-1]["text"] == "entry_699"
        surviving_indices = [int(r["text"].split("_")[1]) for r in result]
        assert surviving_indices == list(range(200, 700))

    def test_oldest_entries_are_dropped(self, tmp_path):
        f = tmp_path / "transcript.jsonl"
        entries = [_make_user_entry(i) for i in range(self.TOTAL_ENTRIES)]
        _write_entries(f, entries)
        result = scrape_transcript(str(f))
        all_texts = {r["text"] for r in result}
        for idx in [0, 50, 100, 199]:
            assert f"entry_{idx}" not in all_texts

    def test_mixed_user_assistant_cap(self, tmp_path):
        f = tmp_path / "transcript.jsonl"
        entries = []
        for i in range(self.TOTAL_ENTRIES):
            entries.append(_make_user_entry(i))
            entries.append(_make_assistant_entry(i))
        _write_entries(f, entries)
        result = scrape_transcript(str(f))
        assert len(result) == _MAX_ENTRIES
        user_entries = [r for r in result if r["role"] == "user"]
        assistant_entries = [r for r in result if r["role"] == "assistant"]
        assert len(user_entries) == 250
        assert len(assistant_entries) == 250
        last_user_idx = int(user_entries[-1]["text"].split("_")[1])
        assert last_user_idx == 699
        first_user_idx = int(user_entries[0]["text"].split("_")[1])
        assert first_user_idx == 450

    def test_under_cap_returns_all(self, tmp_path):
        f = tmp_path / "transcript.jsonl"
        entries = [_make_user_entry(i) for i in range(50)]
        _write_entries(f, entries)
        result = scrape_transcript(str(f))
        assert len(result) == 50
        assert result[0]["text"] == "entry_0"
        assert result[-1]["text"] == "entry_49"

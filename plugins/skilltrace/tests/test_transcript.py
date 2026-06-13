"""Tests for transcript scraper."""

import json
from pathlib import Path

import pytest

from src.transcript import scrape_transcript, _scrape_transcript_impl, _redact_secrets, _scrape_subagent


def _write_entries(path: Path, entries: list[dict]):
    path.write_text(
        "\n".join(json.dumps(e) for e in entries) + "\n",
        encoding="utf-8",
    )


_USER_PROMPT = {"type": "user", "message": {"role": "user", "content": "do the task"}}


def test_empty_file(tmp_path):
    f = tmp_path / "transcript.jsonl"
    f.write_text("")
    assert scrape_transcript(str(f)) == []


def test_missing_file():
    assert scrape_transcript("/nonexistent/path.jsonl") == []


def test_extracts_user_text(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        {"type": "user", "message": {"role": "user", "content": "add auth"}},
    ])
    result = scrape_transcript(str(f))
    assert len(result) == 1
    assert result[0] == {"role": "user", "text": "add auth"}


def test_extracts_user_text_from_list_content(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        _USER_PROMPT,
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "text", "text": "first part"},
            {"type": "text", "text": "second part"},
        ]}},
    ])
    result = scrape_transcript(str(f))
    assert any(e.get("text") == "first part second part" for e in result)


def test_extracts_assistant_text(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        _USER_PROMPT,
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Done. Created the file."},
        ]}},
    ])
    result = scrape_transcript(str(f))
    assert len(result) == 2
    assert result[1]["role"] == "assistant"
    assert result[1]["text"] == "Done. Created the file."


def test_extracts_tool_use(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        _USER_PROMPT,
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Write", "input": {"file_path": "/app.ts", "content": "big"}},
        ]}},
    ])
    result = scrape_transcript(str(f))
    assert result[1]["tools"] == [{"tool": "Write", "params": {"file_path": "/app.ts", "content": "big"}}]


def test_extracts_bash_command(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        _USER_PROMPT,
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "npm test"}},
        ]}},
    ])
    result = scrape_transcript(str(f))
    assert result[1]["tools"][0]["params"] == {"command": "npm test"}


def test_extracts_search_query(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        _USER_PROMPT,
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "mcp__brave-search__brave_web_search", "input": {"query": "JWT guide"}},
        ]}},
    ])
    result = scrape_transcript(str(f))
    assert result[1]["tools"][0]["params"] == {"query": "JWT guide"}


def test_skips_attachment_entries(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        {"type": "attachment", "data": "noisy hook output"},
        {"type": "user", "message": {"role": "user", "content": "real prompt"}},
        {"type": "last-prompt", "data": "skip"},
        {"type": "permission-mode", "data": "skip"},
        {"type": "file-history-snapshot", "data": "skip"},
    ])
    result = scrape_transcript(str(f))
    assert len(result) == 1
    assert result[0]["text"] == "real prompt"


def test_mixed_text_and_tools(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        _USER_PROMPT,
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Creating file now."},
            {"type": "tool_use", "name": "Write", "input": {"file_path": "/x.py", "content": "..."}},
            {"type": "tool_use", "name": "Bash", "input": {"command": "pytest"}},
        ]}},
    ])
    result = scrape_transcript(str(f))
    assert result[1]["text"] == "Creating file now."
    assert len(result[1]["tools"]) == 2


def test_truncates_long_text(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        {"type": "user", "message": {"role": "user", "content": "x" * 5000}},
    ])
    result = scrape_transcript(str(f))
    assert len(result[0]["text"]) == 3000


def test_max_entries_cap(tmp_path):
    f = tmp_path / "t.jsonl"
    entries = [
        {"type": "user", "message": {"role": "user", "content": f"msg {i}"}}
        for i in range(600)
    ]
    _write_entries(f, entries)
    result = scrape_transcript(str(f))
    assert len(result) == 500


def test_skips_thinking_blocks(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        _USER_PROMPT,
        {"type": "assistant", "message": {"content": [
            {"type": "thinking", "thinking": "internal reasoning..."},
            {"type": "text", "text": "visible response"},
        ]}},
    ])
    result = scrape_transcript(str(f))
    assert "thinking" not in json.dumps(result)
    assert result[1]["text"] == "visible response"


def test_skips_empty_user_content(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        {"type": "user", "message": {"role": "user", "content": ""}},
        {"type": "user", "message": {"role": "user", "content": "   "}},
    ])
    assert scrape_transcript(str(f)) == []


def test_agent_tool_params(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        _USER_PROMPT,
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Agent", "input": {
                "description": "Review code", "subagent_type": "code-reviewer",
                "prompt": "long prompt text here..."
            }},
        ]}},
    ])
    result = scrape_transcript(str(f))
    params = result[1]["tools"][0]["params"]
    assert params == {"description": "Review code", "subagent_type": "code-reviewer", "prompt": "long prompt text here..."}


def test_captures_agent_tool_result(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        _USER_PROMPT,
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "tool_123", "name": "Agent", "input": {
                "description": "Review auth", "subagent_type": "code-reviewer",
            }},
        ]}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "tool_123", "content": [
                {"type": "text", "text": "Found 2 security issues in auth module."}
            ]},
        ]}},
    ])
    result = scrape_transcript(str(f))
    assert len(result) == 3
    assert result[2]["role"] == "tool_results"
    assert result[2]["tool_results"][0]["tool"] == "Agent"
    assert "security issues" in result[2]["tool_results"][0]["result"]


def test_captures_tool_result_string_content(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        _USER_PROMPT,
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "tool_456", "name": "Bash", "input": {"command": "npm test"}},
        ]}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "tool_456", "content": "5 tests passed"},
        ]}},
    ])
    result = scrape_transcript(str(f))
    assert result[2]["role"] == "tool_results"
    assert result[2]["tool_results"][0]["result"] == "5 tests passed"


def test_skips_untracked_tool_results(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "unknown_id", "content": "should be skipped"},
        ]}},
    ])
    result = scrape_transcript(str(f))
    assert result == []


def test_truncates_long_tool_result(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        _USER_PROMPT,
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "tool_789", "name": "Agent", "input": {"description": "big report"}},
        ]}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "tool_789", "content": "x" * 8000},
        ]}},
    ])
    result = scrape_transcript(str(f))
    assert len(result[2]["tool_results"][0]["result"]) == 5000


def test_tool_result_with_text(tmp_path):
    f = tmp_path / "t.jsonl"
    _write_entries(f, [
        _USER_PROMPT,
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "tool_abc", "name": "Bash", "input": {"command": "ls"}},
        ]}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "text", "text": "now fix the bug"},
            {"type": "tool_result", "tool_use_id": "tool_abc", "content": "file1.py file2.py"},
        ]}},
    ])
    result = scrape_transcript(str(f))
    assert result[2]["role"] == "tool_results"
    assert result[2]["text"] == "now fix the bug"
    assert result[2]["tool_results"][0]["result"] == "file1.py file2.py"


def _make_prompt(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def _make_assistant(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _make_tool_use(name, inp, tool_id="t1"):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": tool_id, "name": name, "input": inp},
    ]}}


def _turn_end():
    return {"type": "system", "subtype": "turn_duration", "duration_ms": 100}


def _multi_prompt_transcript():
    return [
        _make_prompt("build roguelike"),          # index 0 → prompt_indices[0]
        _make_tool_use("Write", {"file_path": "/game.html", "content": "big game"}),  # 1
        _make_assistant("Done building game."),    # 2
        _turn_end(),                               # 3
        _make_prompt("how much did that cost?"),   # 4 → prompt_indices[1]
        _make_assistant("About $0.40 wasted."),    # 5
        _turn_end(),                               # 6
        _make_prompt("ok fix the hook"),           # 7 → prompt_indices[2]
        _make_tool_use("Edit", {"file_path": "/gate.sh", "old_string": "a", "new_string": "b"}),  # 8
        _make_assistant("Fixed."),                 # 9
        _turn_end(),                               # 10
        _make_prompt("current prompt"),            # 11 → prompt_indices[3]
    ]


class TestSecretRedaction:
    def test_redacts_bearer_token(self):
        assert "[REDACTED]" in _redact_secrets("Authorization: Bearer sk-live-abc123xyz")

    def test_redacts_api_key(self):
        assert "[REDACTED]" in _redact_secrets("api_key=super_secret_key_123")

    def test_redacts_password(self):
        assert "[REDACTED]" in _redact_secrets("password=hunter2")

    def test_redacts_github_token(self):
        assert "[REDACTED]" in _redact_secrets("GITHUB_TOKEN=ghp_" + "a" * 30)

    def test_redacts_github_oauth(self):
        assert "[REDACTED]" in _redact_secrets("token: gho_" + "b" * 30)

    def test_redacts_sk_live(self):
        assert "[REDACTED]" in _redact_secrets("key: sk-live-abc123")

    def test_redacts_sk_proj(self):
        assert "[REDACTED]" in _redact_secrets("sk-proj-my_project_key")

    def test_redacts_url_credentials(self):
        result = _redact_secrets("https://user:pass@example.com/api")
        assert "pass" not in result

    def test_redacts_aws_secret(self):
        assert "[REDACTED]" in _redact_secrets("AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG")

    def test_redacts_aws_access_key_id(self):
        result = _redact_secrets("AKIAIOSFODNN7EXAMPLE")
        assert "IOSFODNN7EXAMPLE" not in result

    def test_redacts_jwt(self):
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyIiwibmFtZSI6IkpvaG4ifQ.signature"
        result = _redact_secrets(jwt)
        assert "eyJzdWIi" not in result

    def test_redacts_sk_ant(self):
        assert "[REDACTED]" in _redact_secrets("sk-ant-api03-my_key_here")

    def test_redacts_pem_key(self):
        result = _redact_secrets("-----BEGIN PRIVATE KEY-----")
        assert "PRIVATE KEY" not in result

    def test_redacts_postgres_connection(self):
        result = _redact_secrets("postgres://admin:secret@db.host:5432/mydb")
        assert "secret" not in result

    def test_preserves_normal_text(self):
        text = "Hello world, this is normal text with no secrets."
        assert _redact_secrets(text) == text


class TestBoundaryWindowing:

    def test_default_no_boundary_uses_last_two(self, tmp_path):
        f = tmp_path / "t.jsonl"
        _write_entries(f, _multi_prompt_transcript())
        entries, boundary = _scrape_transcript_impl(str(f))
        assert boundary == 11
        assert any("fix the hook" in str(e) for e in entries)
        assert any("gate.sh" in str(e) for e in entries)
        assert any("roguelike" in str(e) for e in entries) is False
        assert any("current prompt" in str(e) for e in entries) is False

    def test_boundary_expands_window(self, tmp_path):
        f = tmp_path / "t.jsonl"
        _write_entries(f, _multi_prompt_transcript())
        entries, boundary = _scrape_transcript_impl(str(f), lower_boundary=0)
        assert boundary == 11
        assert any("roguelike" in str(e) for e in entries)
        assert any("game.html" in str(e) for e in entries)
        assert any("gate.sh" in str(e) for e in entries)

    def test_boundary_at_middle_prompt(self, tmp_path):
        f = tmp_path / "t.jsonl"
        _write_entries(f, _multi_prompt_transcript())
        entries, boundary = _scrape_transcript_impl(str(f), lower_boundary=4)
        assert boundary == 11
        assert any("how much" in str(e) for e in entries)
        assert any("gate.sh" in str(e) for e in entries)
        assert any("roguelike" in str(e) for e in entries) is False

    def test_boundary_beyond_all_prompts_falls_back(self, tmp_path):
        f = tmp_path / "t.jsonl"
        _write_entries(f, _multi_prompt_transcript())
        entries, boundary = _scrape_transcript_impl(str(f), lower_boundary=999)
        assert boundary == 11
        assert any("gate.sh" in str(e) for e in entries)

    def test_returns_none_boundary_for_empty(self, tmp_path):
        f = tmp_path / "t.jsonl"
        f.write_text("")
        entries, boundary = _scrape_transcript_impl(str(f))
        assert entries == []
        assert boundary is None

    def test_single_prompt_ignores_boundary(self, tmp_path):
        f = tmp_path / "t.jsonl"
        _write_entries(f, [
            _make_prompt("only prompt"),
            _make_assistant("response"),
        ])
        entries, boundary = _scrape_transcript_impl(str(f), lower_boundary=0)
        assert boundary == 0
        assert any("only prompt" in str(e) for e in entries)

    def test_public_api_unchanged(self, tmp_path):
        f = tmp_path / "t.jsonl"
        _write_entries(f, _multi_prompt_transcript())
        result = scrape_transcript(str(f))
        assert isinstance(result, list)
        assert any("gate.sh" in str(e) for e in result)


class TestSubagentScraping:

    def test_extracts_write_tool(self, tmp_path):
        sa = tmp_path / "agent-123.jsonl"
        sa.write_text(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Write", "input": {"file_path": "/app.py", "content": "code"}}
        ]}}) + "\n", encoding="utf-8")
        actions = _scrape_subagent(sa)
        assert len(actions) == 1
        assert actions[0]["tool"] == "Write"

    def test_extracts_bash_tool(self, tmp_path):
        sa = tmp_path / "agent-456.jsonl"
        sa.write_text(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "npm install"}}
        ]}}) + "\n", encoding="utf-8")
        actions = _scrape_subagent(sa)
        assert len(actions) == 1
        assert actions[0]["tool"] == "Bash"
        assert actions[0]["params"]["command"] == "npm install"

    def test_skips_read_tools(self, tmp_path):
        sa = tmp_path / "agent-789.jsonl"
        sa.write_text(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": "/app.py"}}
        ]}}) + "\n", encoding="utf-8")
        actions = _scrape_subagent(sa)
        assert len(actions) == 0

    def test_skips_wrapper_commands(self, tmp_path):
        sa = tmp_path / "agent-abc.jsonl"
        sa.write_text(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "bash wrapper.sh init"}}
        ]}}) + "\n", encoding="utf-8")
        actions = _scrape_subagent(sa)
        assert len(actions) == 0

    def test_nonexistent_file_returns_empty(self, tmp_path):
        sa = tmp_path / "nonexistent.jsonl"
        assert _scrape_subagent(sa) == []

    def test_extracts_mcp_tools(self, tmp_path):
        sa = tmp_path / "agent-mcp.jsonl"
        sa.write_text(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "mcp__brave__search", "input": {"query": "test"}}
        ]}}) + "\n", encoding="utf-8")
        actions = _scrape_subagent(sa)
        assert len(actions) == 1
        assert actions[0]["tool"] == "mcp__brave__search"

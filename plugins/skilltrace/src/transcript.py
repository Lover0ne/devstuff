"""Transcript scraper — extracts clean entries from Claude Code's transcript JSONL.

Filters out noise (hook outputs, metadata, system entries) and returns
user prompts + assistant actions (text, tool_use with key params only).
"""

import json
import re
from pathlib import Path

_MAX_TEXT_LEN = 3000

_SECRET_PATTERNS = [
    (re.compile(r'(Bearer\s+)\S+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(api[_-]?key\s*[=:]\s*)\S+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(password\s*[=:]\s*)\S+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(secret\s*[=:]\s*)\S+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(token\s*[=:]\s*)\S+', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'https?://[^@\s]+@'), 'https://[REDACTED]@'),
    (re.compile(r'(AWS_SECRET_ACCESS_KEY\s*[=:]\s*)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(GITHUB_TOKEN\s*[=:]\s*)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(ghp_)\S{30,}'), r'\1[REDACTED]'),
    (re.compile(r'(gho_)\S{30,}'), r'\1[REDACTED]'),
    (re.compile(r'(sk-live-)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(sk-proj-)\S+'), r'\1[REDACTED]'),
]


def _redact_secrets(text: str) -> str:
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
_MAX_ENTRIES = 500
_MAX_PARAM_LEN = 3000

_TOOL_KEY_PARAMS = {
    "Write": ["file_path", "content"],
    "Edit": ["file_path", "old_string", "new_string"],
    "Read": ["file_path"],
    "Bash": ["command"],
    "PowerShell": ["command"],
    "Glob": ["pattern"],
    "Grep": ["pattern", "path"],
    "Agent": ["description", "subagent_type", "prompt"],
    "Skill": ["skill"],
    "NotebookEdit": ["notebook_path", "new_source"],
}

_MAX_RESULT_LEN = 5000


def _truncate_param(value: str) -> str:
    if isinstance(value, str) and len(value) > _MAX_PARAM_LEN:
        return value[:_MAX_PARAM_LEN]
    return value


def _extract_tool_params(tool_name: str, tool_input: dict) -> dict:
    keys = _TOOL_KEY_PARAMS.get(tool_name)
    if keys:
        return {k: _truncate_param(tool_input[k]) for k in keys if k in tool_input}
    if "search" in tool_name.lower():
        q = tool_input.get("query")
        return {"query": q} if q else {}
    if "fetch" in tool_name.lower() or "navigate" in tool_name.lower():
        u = tool_input.get("url")
        return {"url": u} if u else {}
    return {}


def _extract_tool_result_text(block: dict) -> str:
    content = block.get("content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for sub in content:
            if isinstance(sub, dict) and sub.get("type") == "text":
                parts.append(sub.get("text", ""))
        return " ".join(parts).strip()
    return ""


def _process_user(entry: dict, pending_tools: dict, filtered_tool_ids: set) -> dict | None:
    msg = entry.get("message", {})
    content = msg.get("content")
    if not content:
        return None
    if isinstance(content, str):
        text = content.strip()
        if not text:
            return None
        if "skilltrace" in text.lower() and ("<command-" in text or "[SKILLTRACE]" in text or "skilltrace:" in text):
            return None
        return {"role": "user", "text": text[:_MAX_TEXT_LEN]}
    if entry.get("isMeta"):
        text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"] if isinstance(content, list) else []
        if any("wrapper.sh" in t for t in text_parts):
            return None
    if not isinstance(content, list):
        return None
    texts = []
    tool_results = []
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            t = block.get("text", "").strip()
            if t:
                texts.append(t)
        elif btype == "tool_result":
            tid = block.get("tool_use_id", "")
            if tid in filtered_tool_ids:
                continue
            tool_name = pending_tools.get(tid)
            if not tool_name:
                continue
            result_text = _extract_tool_result_text(block)
            if result_text:
                tool_results.append({
                    "tool": tool_name,
                    "result": result_text[:_MAX_RESULT_LEN],
                })
    if not texts and not tool_results:
        return None
    if tool_results:
        result = {"role": "tool_results", "tool_results": tool_results}
        if texts:
            result["text"] = " ".join(texts)[:_MAX_TEXT_LEN]
        return result
    return {"role": "user", "text": " ".join(texts)[:_MAX_TEXT_LEN]}


def _process_assistant(entry: dict, pending_tools: dict, filtered_tool_ids: set) -> dict | None:
    msg = entry.get("message", {})
    content = msg.get("content")
    if not content or not isinstance(content, list):
        return None
    result = {"role": "assistant"}
    texts = []
    tools = []
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            t = block.get("text", "").strip()
            if t:
                texts.append(t[:_MAX_TEXT_LEN])
        elif btype == "tool_use":
            name = block.get("name", "unknown")
            tool_id = block.get("id", "")
            if tool_id:
                pending_tools[tool_id] = name
            inp = block.get("input", {})
            if isinstance(inp, dict) and "wrapper.sh" in str(inp.get("command", "")):
                if tool_id:
                    filtered_tool_ids.add(tool_id)
                continue
            params = _extract_tool_params(name, inp if isinstance(inp, dict) else {})
            tool_entry = {"tool": name}
            if params:
                tool_entry["params"] = params
            tools.append(tool_entry)
    if texts:
        result["text"] = " ".join(texts)
        if len(result["text"]) > _MAX_TEXT_LEN:
            result["text"] = result["text"][:_MAX_TEXT_LEN]
    if tools:
        result["tools"] = tools
    if "text" not in result and "tools" not in result:
        return None
    return result


_SUBAGENT_ACTION_TOOLS = {"Write", "Edit", "Bash", "PowerShell"}


def _scrape_subagent(subagent_path: Path) -> list[dict]:
    if not subagent_path.exists():
        return []
    actions = []
    try:
        with open(subagent_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "assistant":
                    continue
                msg = entry.get("message", {})
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    name = block.get("name", "")
                    if name not in _SUBAGENT_ACTION_TOOLS and not name.startswith("mcp__"):
                        continue
                    inp = block.get("input", {})
                    if not isinstance(inp, dict):
                        continue
                    if "wrapper.sh" in str(inp.get("command", "")):
                        continue
                    params = _extract_tool_params(name, inp)
                    tool_entry = {"tool": name}
                    if params:
                        tool_entry["params"] = params
                    actions.append(tool_entry)
    except OSError:
        return []
    return actions


def _redact_entry(entry: dict) -> dict:
    for key in ("text",):
        if key in entry and isinstance(entry[key], str):
            entry[key] = _redact_secrets(entry[key])
    if "tools" in entry:
        for tool in entry["tools"]:
            if "params" in tool:
                for k, v in tool["params"].items():
                    if isinstance(v, str):
                        tool["params"][k] = _redact_secrets(v)
    if "tool_results" in entry:
        for tr in entry["tool_results"]:
            if "result" in tr and isinstance(tr["result"], str):
                tr["result"] = _redact_secrets(tr["result"])
    return entry


def _is_real_user_prompt(entry: dict) -> bool:
    if entry.get("type") != "user":
        return False
    if entry.get("isMeta"):
        return False
    if entry.get("interruptedMessageId"):
        return False
    msg = entry.get("message", {})
    content = msg.get("content")
    if not isinstance(content, str):
        return False
    text = content.strip()
    if not text:
        return False
    if text.startswith("<command-") or text.startswith("<local-command"):
        return False
    if text.startswith("[Request interrupted"):
        return False
    return True


def scrape_transcript(transcript_path: str) -> list[dict]:
    path = Path(transcript_path).resolve()
    if ".." in path.parts:
        return []
    if not path.suffix == ".jsonl":
        return []
    if not path.exists():
        return []
    pending_tools: dict[str, str] = {}
    filtered_tool_ids: set[str] = set()
    results = []
    prompt_indices = []
    subagent_refs: list[tuple[int, str, str]] = []
    raw_index = 0
    turn_ended = True
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") == "system" and entry.get("subtype") == "turn_duration":
                turn_ended = True
            if _is_real_user_prompt(entry) and turn_ended:
                prompt_indices.append(raw_index)
                turn_ended = False
            etype = entry.get("type")
            if etype == "user":
                tr = entry.get("toolUseResult")
                if isinstance(tr, dict) and tr.get("isAsync") and tr.get("agentId"):
                    agent_id = tr["agentId"]
                    desc = tr.get("description", "") + " " + tr.get("prompt", "")
                    if "skilltrace" not in desc.lower():
                        subagent_refs.append((raw_index, agent_id, tr.get("description", "")))
                processed = _process_user(entry, pending_tools, filtered_tool_ids)
                if processed:
                    results.append((raw_index, processed))
            elif etype == "assistant":
                processed = _process_assistant(entry, pending_tools, filtered_tool_ids)
                if processed:
                    results.append((raw_index, processed))
            raw_index += 1
    if len(prompt_indices) >= 2:
        lower = prompt_indices[-2]
        upper = prompt_indices[-1]
        results = [(i, r) for i, r in results if lower <= i < upper]
        subagent_refs = [(i, aid, desc) for i, aid, desc in subagent_refs if lower <= i < upper]
    results = [r for _, r in results]
    if len(results) > _MAX_ENTRIES:
        results = results[-_MAX_ENTRIES:]
    results = [_redact_entry(r) for r in results]
    if subagent_refs:
        subagent_dir = path.parent / "subagents"
        for _, agent_id, desc in subagent_refs:
            sa_path = subagent_dir / f"agent-{agent_id}.jsonl"
            actions = _scrape_subagent(sa_path)
            if actions:
                results.append({
                    "role": "subagent",
                    "description": desc,
                    "actions": [_redact_entry({"tools": [a]}).get("tools", [a])[0] for a in actions],
                })
    return results

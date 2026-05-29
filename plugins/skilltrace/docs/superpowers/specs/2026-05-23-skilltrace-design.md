# Skilltrace — Design Specification

> A Claude Code plugin that automatically traces user+LLM activities and converts completed tasks into replayable, context-specific skills.

## 1. Problem Statement

Knowledge generated during Claude Code sessions is ephemeral. When a developer sets up an MCP server for Client X, deploys a service, or writes a migration script, the procedural knowledge dies with the session. Repeating the same task requires re-discovering the same steps.

Skilltrace captures this procedural knowledge automatically, producing specific, replayable skills without user intervention.

## 2. Core Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Architecture | Pure Hook Pipeline | Zero external dependencies, proven pattern (ralph-loop) |
| Task boundary detection | Automatic heuristic | No user friction |
| Processing trigger | UserPromptSubmit + SessionEnd fallback | Non-blocking, natural boundary signal |
| Tracking scope | All tool activity | Extraction agent filters relevance |
| Skill storage | `~/.claude/skills/` (global auto-discovery), metadata in `~/.claude/skilltrace/` | Native Claude Code format, visible in every project |
| Skill updates | Auto-update with version history | No user friction, versioned rollback |
| Deduplication | Registry + fuzzy matching | Semi-deterministic, scalable |
| Privacy | Local-only, `.skilltrace-ignore` for exclusions | Minimal v1 controls |
| Enable/disable | State file + `/skilltrace:pause` and `/skilltrace:resume` | Deterministic, persistent |
| Hook language | Python core, bash wrapper | JSON parsing, fuzzy matching, maintainability |
| Dependencies | `rapidfuzz` only, manual TF-IDF | Lightweight install (~5MB) |

## 3. Plugin Structure

```
skilltrace/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── skills/
│   └── skilltrace-manage/
│       └── SKILL.md             # User skill: list, search, replay generated skills
├── commands/
│   ├── status.md                # /skilltrace:status
│   ├── pause.md                 # /skilltrace:pause
│   ├── resume.md                # /skilltrace:resume
│   └── reindex.md               # /skilltrace:reindex — rebuild registry from SKILL.md files
├── hooks/
│   ├── hooks.json               # Hook definitions
│   └── wrapper.sh               # Minimal bash wrapper → calls Python
├── agents/
│   └── skill-extractor.md       # Subagent: activity log → SKILL.md
├── src/
│   ├── __init__.py
│   ├── cli.py                   # Entry point (called by wrapper.sh); also exposes "checkpoint" command for deterministic writes
│   ├── collector.py             # PostToolUse handler: append to activity log
│   ├── boundary.py              # Heuristic task boundary detection
│   ├── registry.py              # Registry CRUD operations
│   ├── matcher.py               # Skill matching: TF-IDF + fuzzy (rapidfuzz)
│   ├── config.py                # Enable/disable, paths, settings
│   └── shared.py                # Common utilities
├── scripts/
│   └── setup.sh                 # First-run: create dirs, install deps
├── requirements.txt             # rapidfuzz
├── README.md
└── LICENSE
```

## 4. Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                    USER SESSION                          │
│                                                         │
│  User works normally                                    │
│       │                                                 │
│       ▼                                                 │
│  [PostToolUse hook] ──► collector.py                    │
│       │                   │                             │
│       │                   ▼                             │
│       │              activity.jsonl                     │
│       │              (append one JSON line per call)    │
│       │                                                 │
│  User sends new prompt                                  │
│       │                                                 │
│       ▼                                                 │
│  [UserPromptSubmit hook] ──► boundary.py                │
│       │                        │                        │
│       │                   Log user prompt to            │
│       │                   activity.jsonl (always)       │
│       │                        │                        │
│       │                   ┌────┴────┐                   │
│       │                   │ Score   │                   │
│       │                   │ > 0.6?  │                   │
│       │                   └────┬────┘                   │
│       │                   no   │   yes                  │
│       │                   │    │                        │
│       │                   │    ▼                        │
│       │                   │   Pre-filter gates          │
│       │                   │    │                        │
│       │                   │    ▼                        │
│       │                   │   matcher.py                │
│       │                   │    │                        │
│       │                   │   ┌┴───────┐                │
│       │                   │   │Registry│                │
│       │                   │   │ match? │                │
│       │                   │   └┬───────┘                │
│       │                   │   no │  yes                 │
│       │                   │    │   │                    │
│       │                   │    ▼   ▼                    │
│       │                   │  "create" "update:[IDs]"    │
│       │                   │    │   │                    │
│       │                   │    └───┘                    │
│       │                   │      │                      │
│       │                   ▼      ▼                      │
│       │              Return additionalContext:          │
│       │              - ALWAYS: "call checkpoint tool"   │
│       │              - IF boundary: "write task summary │
│       │                + spawn skill-extractor"         │
│       │                     │                           │
│       │                     ▼                           │
│       │              Claude calls checkpoint tool       │
│       │              → cli.py writes to activity.jsonl  │
│       │              (deterministic, atomic)            │
│       │                     │                           │
│       │              IF boundary:                       │
│       │              Claude spawns skill-extractor      │
│       │              (background subagent with summary  │
│       │               + activity log path + match)      │
│       │                     │                           │
│       │                     ▼                           │
│       │              SKILL.md written/updated           │
│       │              registry.json updated              │
│       │              activity.jsonl rotated             │
│       │                                                 │
│  [SessionEnd hook] ──► Same flow for last task          │
└─────────────────────────────────────────────────────────┘
```

## 5. Component Specifications

### 5.1 Hook Definitions (hooks.json)

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh\" setup"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh\" collect"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh\" boundary"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh\" finalize"
          }
        ]
      }
    ]
  }
}
```

### 5.2 Wrapper Script (hooks/wrapper.sh)

```bash
#!/bin/bash
INPUT=$(cat)
echo "$INPUT" | python3 "${CLAUDE_PLUGIN_ROOT}/src/cli.py" "$1"
```

Three lines. All logic in Python.

### 5.3 Activity Log Format (activity.jsonl)

Three entry types, all appended to a single JSONL file:

**Tool call entry** (appended by `collector.py` via PostToolUse hook):

```json
{
  "ts": "2026-05-23T15:30:00Z",
  "type": "tool",
  "tool": "Write",
  "input": {"file_path": "/project/src/server.ts", "content": "...truncated..."},
  "result_summary": "File written successfully",
  "session_id": "abc123"
}
```

**Prompt entry** (appended by `boundary.py` via UserPromptSubmit hook):

```json
{
  "ts": "2026-05-23T15:29:00Z",
  "type": "prompt",
  "text": "configurami un MCP server per Client X con auth custom e PostgreSQL",
  "session_id": "abc123"
}
```

**Checkpoint entry** (written deterministically by `cli.py checkpoint` command, invoked by Claude as tool call):

```json
{
  "ts": "2026-05-23T15:31:00Z",
  "type": "checkpoint",
  "summary": "Configured PostgreSQL connection pool in src/server.ts with SSL and connection limits.",
  "session_id": "abc123"
}
```

Every UserPromptSubmit, the hook returns `additionalContext` instructing main Claude to call the `skilltrace-checkpoint` tool with a 1-sentence summary. The tool (not Claude) writes the entry atomically to activity.jsonl, following the JanusLM deterministic-write pattern:
- Tool call = guaranteed write (Python controls format and atomicity)
- `Path.write_text()` for atomic OS-level write
- JSON receipt printed to stdout confirming write
- Claude cannot alter the entry format — only provides the summary text as argument
- Missing checkpoint is detectable (no receipt in tool output)

Rules:
- `content` and `result` fields truncated to 500 chars max
- Prompt `text` stored in full (critical for intent reconstruction)
- File path always stored in full (critical for matching)
- Max log size: 10MB, then rotate (rename to `.old`, start fresh)

### 5.4 Boundary Detection (boundary.py)

Scoring heuristic applied when UserPromptSubmit fires. The current prompt is used **only for boundary detection** (topic comparison). All gate checks below analyze the **previous task's** activity log and prompts.

| Signal | Weight | Implementation |
|---|---|---|
| File path shift | 30% | Jaccard distance of directory sets between current and previous activity block |
| Tool pattern change | 20% | Cosine similarity of tool frequency vectors |
| Time gap | 20% | Minutes since last tool call. >5min = 1.0, <1min = 0.0, linear interpolation |
| Topic keywords | 15% | TF-IDF (manual) cosine similarity between previous and current prompt |
| Explicit markers | 15% | Regex scan for boundary phrases: "now let's", "next", "switch to", "new task", "moving on" |

**Score > 0.6** → boundary detected, proceed to pre-filter gates.

**Guard rails:**
- First activity of session → no boundary (nothing to extract)
- Activity block < 3 tool calls → skip (not a meaningful task)

**Pre-filter gates (deterministic, before agent spawn):**

All three gates must pass. If any fails, skip extraction (log reason to debug.log).

| Gate | Check | Rationale |
|---|---|---|
| Boundary score | > 0.6 | Task switch detected |
| Activity signature | ≥3 mutating tool calls (Write, Edit, Bash) in previous block | Read-only activity (Read/Grep/Glob) is exploration, not a replicable task |
| Prompt classification | Regex on previous task's prompts: skip patterns (`^(what|why|how does|explain|review|check|debug|show me)`) → skip. Action patterns (`create|build|set up|deploy|write|implement|add|configure|migrate`) → proceed | Questions and reviews don't produce replicable procedures |

### 5.5 Registry (registry.json)

```json
{
  "version": 1,
  "skills": [
    {
      "id": "mcp-server-client-x",
      "name": "Setting up MCP Server for Client X",
      "description": "Use when setting up an MCP server for Client X with custom auth and PostgreSQL backend.",
      "tags": ["mcp", "server", "client-x", "setup", "postgresql"],
      "files_touched": ["src/server.ts", "package.json", ".mcp.json"],
      "tools_used": ["Write", "Bash", "Edit"],
      "created": "2026-05-23T15:00:00Z",
      "updated": "2026-05-23T16:00:00Z",
      "version": 1,
      "path": "mcp-server-client-x/SKILL.md"
    }
  ]
}
```

### 5.6 Skill Matching (matcher.py)

Two-phase matching (inspired by JanusLM `validate_domain.py`):

**Phase 1 — Deterministic pre-filter (Python, no LLM):**
- Extract from current activity: file paths, tool names, bash commands
- Generate tags from activity data (directory names, file extensions, command patterns)
- For each registry entry, compute overlap score:
  - File path overlap (Jaccard): 40%
  - Tag overlap (fuzzy, rapidfuzz ratio threshold 85%): 35%
  - Tool pattern overlap (set intersection): 25%
- Return entries with overlap > 0.5 as candidates (max 3)

**Phase 2 — Agent decision (only if candidates found):**
- Pass candidate skill IDs + paths to skill-extractor agent
- Agent reads only those 2-3 candidate skills
- Agent decides: update existing or create new

### 5.7 Skill Extractor Agent (agents/skill-extractor.md)

Subagent receives via Agent tool prompt (constructed by main Claude):
- **Task summary**: 2-3 sentence summary written by main Claude on boundary detection, capturing intent, context, corrections, and outcome. Main Claude has full conversation context so this captures what raw logs cannot (business context, reasoning, abandoned approaches).
- **Activity log path**: `~/.claude/skilltrace/activity.jsonl` — subagent reads the segment between previous boundary and current boundary. Contains tool calls, user prompts, and checkpoint summaries.
- **Match result**: "create_new" or "update: [id1, id2]" (from matcher.py)

**Quality gate (agent MUST enforce):**

Agent MUST skip extraction and produce no SKILL.md when:
- Cannot determine a clear, replicable purpose from the activity
- Activity is purely reactive (typo fixes, linting, formatting)
- Cannot write a meaningful "Use when..." description
- Activity log is incoherent or too fragmented to reconstruct a procedure

On skip: log reason to `debug.log` with timestamp and activity summary. Activity log preserved for potential retry on next trigger.

**Course correction handling:**

When activity log contains correction prompts ("no", "change", "instead", "anzi", "cambia", "piuttosto", "actually", "wait", "scratch that"):
1. Identify the FINAL stable approach (last consistent sequence of tool calls)
2. DISCARD tool calls from abandoned approaches
3. Reflect ONLY what user ultimately wanted in the skill
4. If multiple corrections make the final intent unclear → trigger quality gate (skip)

**Multi-task splitting:**

Agent MUST analyze activity log for clusters of independent activities. If a single block contains operations on clearly distinct domains (different directories, different tool patterns, different purposes), MUST produce separate skills for each cluster. Indicators:
- Tool calls targeting unrelated directory trees
- Distinct tool usage patterns (e.g., Write-heavy block followed by Bash-heavy block on different paths)
- Multiple unrelated user prompts within the block

Each split cluster goes through the full create/update flow independently.

Agent produces SKILL.md following these hard constraints:

**Frontmatter:**
- `name`: kebab-case, 64 chars max, verb-first gerund form ("setting-up-mcp-server-client-x")
- `description`: starts with "Use when...", third person, triggers/symptoms only, NO workflow summary, 1024 chars max

**Body (following Anthropic best practices + superpowers writing-skills):**
- <500 lines total
- Overview: what + core principle in 1-2 sentences
- Prerequisites: tools, packages, access needed
- Steps: numbered, specific, with exact commands/file paths from the actual task
- Reference files: only if >100 lines of reference material, one level deep from SKILL.md
- No narratives. No "we did X". Technique/pattern/reference only.
- SPECIFIC to the actual task context (client name, project name, exact file paths, exact commands used)
- Forward slashes only in paths
- Consistent terminology throughout
- CSO: keywords, symptoms, tool names in description for discovery
- Concise: only add context Claude doesn't already have
- Appropriate degrees of freedom: low for fragile procedures, high for judgment calls

**On update:**
- Save previous version to `~/.claude/skilltrace/versions/{skill-id}/v{N}.md`
- Merge new steps/changes into existing skill in `~/.claude/skills/{skill-id}/SKILL.md`
- Bump version in registry

**On create:**
- Write SKILL.md to `~/.claude/skills/{skill-id}/SKILL.md` (global auto-discovery)
- Add entry to registry.json via `registry.py add`
- Save version snapshot to `~/.claude/skilltrace/versions/{skill-id}/v1.md`

### 5.8 Configuration (config.json)

```json
{
  "enabled": true,
  "skills_dir": "~/.claude/skills",
  "versions_dir": "~/.claude/skilltrace/versions",
  "activity_log": "~/.claude/skilltrace/activity.jsonl",
  "registry": "~/.claude/skilltrace/registry.json",
  "debug_log": "~/.claude/skilltrace/debug.log",
  "max_activity_log_mb": 10,
  "boundary_threshold": 0.6,
  "min_tool_calls_for_task": 3,
  "content_truncate_chars": 500
}
```

### 5.9 Setup (SessionStart hook)

On every session start:
1. Check `~/.claude/skilltrace/` exists → if not, create full directory structure
2. Check Python 3 available → if not, log warning (plugin stays dormant)
3. Check `rapidfuzz` installed → if not, run `pip install rapidfuzz` transparently (JanusLM pattern)
4. Check `config.json` exists → if not, create with defaults
5. Return `additionalContext` confirming Skilltrace is active (or dormant if `enabled: false`)

### 5.10 Commands

**`/skilltrace:pause`**: Sets `config.json` → `enabled: false`. All hooks exit 0 immediately when disabled.

**`/skilltrace:resume`**: Sets `config.json` → `enabled: true`. Hooks resume tracking.

**`/skilltrace:status`**: Shows: enabled/disabled, skill count, registry stats, last extraction timestamp.

**`/skilltrace:reindex`**: Reads all SKILL.md files in skills directory, rebuilds `registry.json` from frontmatter. Fixes drift.

### 5.11 Tool Discipline (JanusLM pattern)

All cli.py commands follow these conventions:

**Contract docstring** at module level in `cli.py`:

```python
"""
Skilltrace CLI — deterministic activity tracking and skill extraction.

Commands:
  collect   --stdin        Append tool call entry to activity.jsonl (PostToolUse hook)
  boundary  --stdin        Evaluate task boundary + append prompt (UserPromptSubmit hook)
  checkpoint --summary S   Append checkpoint entry to activity.jsonl (called by Claude as tool)
  finalize  --stdin        End-of-session extraction trigger (SessionEnd hook)
  setup                    First-run directory creation + dependency install (SessionStart hook)
  registry  --add JSON     Add skill entry to registry.json
  registry  --remove ID    Remove skill entry from registry.json
  registry  --list         Print all registry entries as JSON

Inputs:  stdin (hook JSON), --summary (checkpoint text), --add/--remove (registry ops)
Outputs: stdout JSON receipt, stderr JSON errors

If this script fails:
  - FileNotFoundError on activity.jsonl  -> create empty file, continue
  - JSON decode error on registry.json   -> rotate to .old, create fresh
  - Missing rapidfuzz                    -> degrade to exact matching only
"""
```

**Protected files — "never write directly" rules:**

Claude (main agent and subagents) MUST NOT write these files directly via Write/Edit tools. All writes go through cli.py commands:

| File | Write via | Reason |
|---|---|---|
| `activity.jsonl` | `cli.py collect`, `cli.py boundary`, `cli.py checkpoint` | Format + atomicity enforced |
| `registry.json` | `cli.py registry --add/--remove` | Index integrity, dedup |
| `config.json` | `cli.py setup`, `/skilltrace:pause`, `/skilltrace:resume` | Schema validation |

Skills (SKILL.md files) are written by the skill-extractor subagent via standard Write tool — this is intentional since skill content is LLM-generated.

**JSON receipt on every write:**

Every cli.py command that mutates a file prints a JSON receipt to stdout:

```json
{"status": "ok", "action": "checkpoint_written", "file": "activity.jsonl", "ts": "2026-05-23T15:31:00Z"}
```

On failure: JSON error to stderr + `sys.exit(1)`:

```json
{"error": "Invalid summary: empty string", "command": "checkpoint"}
```

**Write atomicity strategy:**

| File | Strategy | Rationale |
|---|---|---|
| `registry.json` | `Path.write_text()` (full rewrite) | Small file (<100KB), always read/modify/write as unit |
| `config.json` | `Path.write_text()` (full rewrite) | Tiny file, infrequent writes |
| `activity.jsonl` | Atomic append (open, write, flush, close) | Append-heavy, can grow to 10MB. Full rewrite too costly |
| `debug.log` | Atomic append | Same rationale as activity.jsonl |

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Error (JSON details on stderr) |
| 2 | Skipped — valid reasons (disabled, no boundary, gate failed). Not an error. |

## 6. Error Handling

Minimal and silent. User never impacted.

| Scenario | Behavior |
|---|---|
| Hook fails (exit 1) | Non-blocking. JSON error logged to debug.log. |
| Hook skips (exit 2) | Normal — gate check failed, reason logged to debug.log. |
| Python missing | Warning in additionalContext. Plugin dormant. |
| rapidfuzz missing | Auto-install on SessionStart. If fails, matching degrades to exact-only. |
| Activity log corrupt | Rotate to `.old`, start fresh. |
| Registry corrupt | Rotate to `.old`, rebuild via `/skilltrace:reindex`. |
| Extraction fails | Activity log preserved for retry on next trigger. |

## 7. Plugin Manifest (plugin.json)

```json
{
  "name": "skilltrace",
  "description": "Automatic activity tracing and skill generation. Converts completed tasks into replayable, context-specific Claude Code skills.",
  "version": "0.1.0",
  "author": {
    "name": "Lorenzo Campagna"
  },
  "license": "MIT"
}
```

## 8. Runtime File Layout

```
~/.claude/skills/                        # Standard Claude Code global skills (auto-discovery)
├── mcp-server-client-x/
│   └── SKILL.md
├── deploy-script-project-y/
│   └── SKILL.md
└── ...

~/.claude/skilltrace/                    # Skilltrace internal data
├── config.json
├── registry.json
├── activity.jsonl
├── activity.jsonl.old
├── debug.log
└── versions/                            # Version history per skill
    ├── mcp-server-client-x/
    │   ├── v1.md
    │   └── v2.md
    └── deploy-script-project-y/
        └── v1.md
```

## 9. Constraints and Non-Goals

**Constraints:**
- All processing local. No remote servers, no APIs, no cloud storage.
- Hook scripts must complete in <1 second (except SessionStart setup).
- Skill extraction is non-blocking.
- Python 3.8+ required. Single dependency: `rapidfuzz`.

**Non-goals for v1:**
- Skill sharing between users
- Embedding-based semantic search
- GUI or web dashboard
- External knowledge base integration
- Automated skill testing (TDD cycle)

## 10. Success Criteria

1. Plugin installs with `claude plugin add` or `--plugin-dir`
2. After 5+ tool calls on a task, switching to a new task triggers skill extraction
3. Generated skill is specific (includes actual file paths, commands, client names)
4. Generated skill follows Anthropic skill best practices
5. Duplicate tasks match existing skills instead of creating new ones
6. `/skilltrace:pause` and `/skilltrace:resume` work deterministically
7. User experiences zero friction — no prompts, no delays, no errors

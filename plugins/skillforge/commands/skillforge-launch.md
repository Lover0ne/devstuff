---
name: skillforge-launch
description: Use when you want to generate utility skills for this project. "generate skills", "skillforge launch", "analyze project and create skills".
---

Generate utility skills for this project. You ARE the analyzer — explore the project directly using your tools.

## Step 1: Explore the project (BLIND — no prior skill knowledge)

Use Glob and Read to understand the project. Read selectively — start broad, go deep where it matters.

**Start with structure:**
- `Glob("**/*")` to see the full file tree
- Identify key directories (src/, scripts/, .github/, docker/, etc.)

**Read manifest/config files first:**
- `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `pom.xml`, `Gemfile` — dependencies and scripts
- `Dockerfile`, `docker-compose.yml` — containerization
- `Makefile`, `Taskfile.yml`, `justfile` — task runners
- `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile` — CI/CD
- `.env.example`, `.env.*.example` — environment setup
- `prisma/schema.prisma`, `migrations/`, `alembic/` — database
- `vite.config.*`, `next.config.*`, `webpack.config.*` — build tools
- `jest.config.*`, `vitest.config.*`, `pytest.ini`, `pyproject.toml` — test config

**Then read key source files** that reveal operations and workflows:
- Entry points (`src/index.*`, `main.*`, `app.*`)
- Scripts directory if present
- README.md for documented workflows

Do NOT read every file. Read what matters for understanding **what operations this project needs**.

## Step 2: Identify utility skills (BLIND list)

Based on what you found, identify ALL utility skills this project would benefit from. Common categories include but are NOT limited to:

- **Deploy automation** — per environment (staging, prod, etc.)
- **Environment management** — env setup, switching, variable docs
- **Service start/stop** — backend, frontend, workers, dev servers
- **Docker/Compose** — build, up, down, rebuild
- **Database** — setup, migrate, seed, reset, backup
- **Comment cleanup** — remove all `//` comments from source files
- **Repo setup** — local clone setup, remote init, contributor onboarding
- **Process documentation** — explain the flow, architecture, data pipeline
- **Test running** — unit, integration, e2e
- **Build** — dev build, production build, CI build
- **Lint/Format** — auto-fix, check, pre-commit

Look for ANY repetitive operation specific to this project. The list above is guidance, not a boundary.

For each skill determine:
- Skill name and category
- Which file paths are relevant (absolute paths the agent must Read)
- A detailed task brief explaining what the skill should document

**IMPORTANT: Do NOT look at previous skills yet.** This list must be generated purely from project analysis to avoid anchor bias.

## Step 3: Fetch previous skill set

Run the deterministic tool to get skills from the previous set (if any):

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" existing-skills
```

This returns a JSON array of the previous skill set for this project. Each entry has: `id`, `name`, `category`, `version`, `description`.

**Extract the set version:** take the maximum `version` value from the array. This is the previous set version. The NEW set version will be `max_version + 1`. If the array is empty, the new set version is `1`.

If the array is empty, skip to Step 5 (no previous set to reconcile).

## Step 4: Verify and reconcile previous skills

For each skill from the previous set that is NOT already covered by your blind list (Step 2):

1. **Quick feasibility check** — verify the operation is still relevant by checking if the key files/commands still exist in the project (use Glob or Read as needed)
2. **If still feasible** — add it to the list, marked as "reproposed from previous set"
3. **If no longer feasible** (files removed, stack changed, etc.) — drop it

Do NOT blindly re-add all previous skills. Each must pass the feasibility check. The project may have changed significantly since the last run.

After reconciliation, merge into a single final list with two categories:
- **New skills** — from your blind analysis
- **Reproposed skills** — from previous set, verified as still feasible

## Step 5: User confirmation (MANDATORY — DO NOT SKIP)

Present the skill list to the user as a numbered text list. For each skill show: name, category, one-line description. Mark reproposed skills with "(reproposed from v{N})".

Show summary: "N new skills, M reproposed from previous set. New set version: v{new_set_version}"

Then use AskUserQuestion with exactly these options:
- **"Yes, launch agents"** — proceed to Step 6
- **"I want changes"** — user writes what to add/remove/modify in the free-text field

**Loop rules:**
- If user selects "Yes, launch agents" → proceed to Step 6
- If user selects "I want changes" → read the free-text notes, adjust the skill list accordingly (add, remove, or modify skills), then re-present the updated list and ask again
- **Repeat until the user selects "Yes, launch agents"**
- You MUST NOT spawn any agents before receiving explicit "Yes" approval
- You MUST NOT proceed without asking — even if the list looks obvious or small

Example AskUserQuestion call:
```
AskUserQuestion({
  questions: [{
    question: "Does this skill list look good?",
    header: "Skills",
    options: [
      { label: "Yes, launch agents", description: "Approve the list and spawn skill-writer agents" },
      { label: "I want changes", description: "Describe what to add, remove, or modify" }
    ],
    multiSelect: false
  }]
})
```

## Step 6: Archive existing skills

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" archive-project
```

Archives ALL existing skills for this project and clears them from registry. Old versions preserved in `.claude/skillforge/versions/` (project-level). This ensures a clean slate — no name-matching needed. Every re-launch produces a fresh complete set.

## Step 7: Spawn agent swarm

Spawn a **background Agent** for EACH approved skill. In each agent prompt include:

1. The skill's task brief, name, and category
2. The list of **absolute file paths** the agent must Read to understand the operation
3. The project_dir (current working directory)
4. The `CLAUDE_PLUGIN_ROOT` value so agent can call wrapper.sh
5. The **set version** (calculated in Step 3: `max_version + 1`, or `1` if first run)
6. Instructions:
   - Read each listed file path
   - Register skill: `bash "${CLAUDE_PLUGIN_ROOT}/hooks/wrapper.sh" skill-write --prepare '{"action":"create","name":"...","tags":[...],"category":"...","project_dir":"...","version":N}'`
   - **The `version` field MUST be the set version passed in the prompt** — do not omit it, do not default to 1
   - Write SKILL.md to the `write_to` path from the response
   - SKILL.md format: frontmatter with `name` (kebab-case) and `description` ("Use when..."), sections: What, Why, How (exact commands), Files, Tags
   - Steps must be reproducible — copy-paste executable, name specific tools
   - Finish in under 15 tool calls

Spawn ALL agents in a single message (parallel launch).

## Step 8: Report

Tell the user: "Skillforge: N utility skills approved (X new, Y reproposed), set v{version}, N agents working in background. Skills will appear in .claude/skills/"

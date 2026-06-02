<h1 align="center">Skillforge</h1>

<p align="center"><strong>Designed for <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a></strong></p>

<p align="center"><strong>Forge utility skills from any project. Automatically.</strong></p>

Skillforge is a Claude Code plugin that analyzes your project structure, identifies repetitive operations, and generates a complete set of utility skills. It does all of this in parallel using an agent swarm.

---

## The Problem

Every project has operations you do over and over: deploying, starting services, managing environments, running migrations, cleaning up code. These patterns end up scattered across config files, READMEs, and team knowledge that never gets written down. When you need them again, you figure them out from scratch.

## The Solution

Run a single command and Skillforge reads your entire project, identifies every automatable operation, and spawns a swarm of agents that each write one focused, reproducible skill. Within minutes you get a full utility skill library tailored to your stack.

## Install

Available from the [devstuff marketplace](https://github.com/Lover0ne/devstuff):

```bash
/plugin marketplace add Lover0ne/devstuff
/plugin install skillforge@devstuff
```

## Usage

```
/skillforge-launch    Analyze project and generate all utility skills
/skillforge-skills    List generated skills (filterable by project)
/skillforge-status    Show skill counts and project info
```

## How It Works

| Phase | What happens |
|-------|-------------|
| **Analyze** | Python scanner reads your project: file tree, configs, manifests, scripts |
| **Identify** | AI analyzes the data and identifies every potential utility skill |
| **Swarm** | One background agent per skill, all running in parallel |
| **Write** | Each agent produces a complete, reproducible SKILL.md |
| **Version** | Re-running `/skillforge-launch` updates existing skills, archives old versions |

## What It Generates

Skillforge doesn't work from a fixed list. It looks at your actual project and figures out what makes sense. Some common examples:

- Deploy automation (per environment)
- Environment setup and switching
- Backend/frontend service start
- Docker/Compose operations
- Database setup, migrations, seeding
- Comment cleanup across source files
- Repository setup and onboarding
- Architecture and flow documentation
- Test execution and coverage
- Build pipelines
- Lint and formatting

...and anything else specific to your project.

## Project Structure

```
skillforge/
├── .claude-plugin/
│   └── plugin.json        # Plugin manifest
├── hooks/
│   ├── hooks.json         # Hook definitions
│   └── wrapper.sh         # Cross-platform dispatcher
├── src/
│   ├── cli.py             # CLI entry point
│   ├── config.py          # Configuration
│   ├── registry.py        # Skill registry CRUD
│   ├── shared.py          # Shared utilities
│   └── skill_ops.py       # Skill creation and versioning
├── agents/
│   └── skill-writer.md    # Background agent that writes individual skills
├── commands/              # Slash commands (launch, status, skills)
├── skills/
│   └── .gitkeep
└── templates/
    └── SKILL.md           # Template for generated skills
```

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Python 3.10+

## License

MIT

---

*One command, every utility skill your project needs.*

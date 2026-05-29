<h1 align="center">Skillforge</h1>

<p align="center"><strong>Designed for <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a></strong></p>

<p align="center"><strong>Forge utility skills from any project. Automatically.</strong></p>

Skillforge is a Claude Code plugin that analyzes your project structure, identifies repetitive operations, and generates a complete set of utility skills — all in parallel via an agent swarm.

---

## The Problem

Every project has operations you repeat: deploying, starting services, managing environments, running migrations, cleaning up code. These patterns live in scattered config files, READMEs, and tribal knowledge. When you need them, you re-discover them from scratch.

## The Solution

One command. Skillforge reads your entire project, identifies every automatable operation, and spawns a swarm of agents — each writing one focused, reproducible skill. In minutes, you have a complete utility skill library tailored to your specific stack.

## Install

```bash
claude plugin add /path/to/skillforge
```

## Usage

```
/skillforge:launch    — Analyze project and generate all utility skills
/skillforge:skills    — List generated skills (filterable by project)
/skillforge:status    — Show skill counts and project info
```

## How It Works

| Phase | What happens |
|-------|-------------|
| **Analyze** | Python scanner reads your project: file tree, configs, manifests, scripts |
| **Identify** | AI analyzes the data and identifies every potential utility skill |
| **Swarm** | One background agent per skill — all run in parallel |
| **Write** | Each agent produces a complete, reproducible SKILL.md |
| **Version** | Re-running `/skillforge:launch` updates existing skills, archives old versions |

## What It Generates

Skillforge doesn't work from a fixed list. It analyzes YOUR project and identifies what makes sense. Common examples:

- Deploy automation (per environment)
- Environment setup and switching
- Backend/frontend service start
- Docker/Compose operations
- Database setup, migrations, seeding
- Comment cleanup across source files
- Repository setup and onboarding
- Architecture and flow documentation
- Test execution
- Build pipelines
- Lint and formatting

...and anything else specific to your project.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Python 3.10+

## License

MIT

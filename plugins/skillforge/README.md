<h1 align="center">Skillforge</h1>

<p align="center"><strong>Designed for <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a></strong></p>

<p align="center"><strong>Forge utility skills from any project. Automatically.</strong></p>

---

## Why I built this

Every project I work on has the same problem: a dozen operations I repeat constantly but never write down. How to deploy staging. How to start the backend with the right env. How to clean up stale Docker containers. How to seed the database after a reset.

I know these things. They live in my head, in scattered config files, in a README someone wrote six months ago that's already outdated. Every time I need one, I re-discover it from scratch. Every time a teammate asks, I explain it from memory.

I kept thinking: I should write all this down as skills. But sitting down to document every utility operation for a project is a full day's work, and I'd rather be building.

So I built Skillforge. You run one command, it reads your project, figures out what operations exist, and spawns a swarm of agents that each write one skill. In a few minutes you have a full utility library tailored to your specific stack. Not generic templates, actual steps extracted from your actual project files.

## How it works

Run `/skillforge-launch` and Skillforge takes it from there:

| Phase | What happens |
|-------|-------------|
| **Analyze** | Reads your project structure, configs, manifests, scripts |
| **Identify** | Figures out every operation worth automating |
| **Swarm** | Spawns one agent per skill, all working in parallel |
| **Write** | Each agent reads the relevant files and writes a complete skill |
| **Version** | Run it again and existing skills get updated, old versions archived |

You get asked to approve the list before agents start writing. Nothing happens without your go-ahead.

## What it generates

Skillforge doesn't work from a fixed list. It looks at your actual project and decides what makes sense. Some things it commonly picks up:

- Deploy automation (per environment)
- Service start commands
- Docker/Compose operations
- Database setup, migrations, seeding
- Environment switching
- Build and lint pipelines
- Repository onboarding steps

But it could be anything. If your project has a specific workflow buried in a Makefile or a shell script, Skillforge will find it and turn it into a skill.

## Install

Available from the [devstuff marketplace](https://github.com/Lover0ne/devstuff):

```bash
/plugin marketplace add Lover0ne/devstuff
/plugin install skillforge@devstuff
```

## Dashboard

Browse your generated skills visually. Run `/skillforge-dashboard` or ask Claude to open it.

<p align="center">
  <img width="100%" alt="Skillforge dashboard" src="https://www-skilltrace.vercel.app/screenshots/skillforge-overview.png" />
</p>

<details>
<summary>Skill viewer</summary>
<p align="center">
  <img width="100%" alt="Skill viewer" src="https://www-skilltrace.vercel.app/screenshots/skillforge-skill-viewer.png" />
</p>
</details>

<details>
<summary>Version compare</summary>
<p align="center">
  <img width="100%" alt="Version compare" src="https://www-skilltrace.vercel.app/screenshots/skillforge-compare.png" />
</p>
</details>

<details>
<summary>Mobile</summary>
<p align="center">
  <img width="300" alt="Mobile view" src="https://www-skilltrace.vercel.app/screenshots/skillforge-mobile.png" />
</p>
</details>

## Commands

| Command | What it does |
|---------|-------------|
| `/skillforge-launch` | Analyze project and generate all utility skills |
| `/skillforge-dashboard` | Open the interactive dashboard in your browser |

You can also just ask Claude: "generate skills for this project", "open skillforge dashboard".

More commands available for inline use (`skillforge-skills`, `skillforge-status`).

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Python 3.10+

## License

MIT

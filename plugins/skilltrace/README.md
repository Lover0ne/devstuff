<p align="center">
  <img width="512" height="279" alt="Skilltrace" src="https://github.com/user-attachments/assets/16f42d7f-9701-453c-b84b-a48a22ab4f19" />
</p>

<h1 align="center">Skilltrace</h1>

<p align="center"><strong>Designed for <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a></strong></p>

<p align="center"><strong>Your work becomes reusable. Automatically.</strong></p>

<p align="center"><a href="https://www-skilltrace.vercel.app/">Visit the official website</a></p>

Skilltrace is a Claude Code plugin that silently watches your coding sessions and converts completed tasks into replayable, self-contained skills. You don't have to do anything.

---

## The Problem

Skills are the most powerful invention in agentic AI. They turn one-time work into reusable knowledge. So I asked myself: why not leverage them at every possible opportunity?

But there are two sides to this problem.

**You can't keep up.** Every time I set up auth, configured a CI pipeline, or wired up an MCP server, I knew that knowledge would evaporate at the end of the session. Next time, I'd start from scratch. Same research, same trial and error, same cost. I wanted to capture everything, but I also just wanted to *work on my projects*. Writing skills means stopping, reflecting, documenting steps, structuring files. It's a second job on top of the actual job.

**Plugins can't keep up either.** Many plugins ship with dozens of skills and keep adding more with every update. The intention is good, but the result is chaos: duplicate skills, overlapping instructions, outdated steps that no one cleans up. Your agent ends up drowning in a pile of skills it can't prioritize, and you end up with more noise than signal. More skills doesn't mean better results.

Skilltrace takes a different approach. It doesn't ship a library of pre-made skills. It **learns yours**, from real work, in your specific stack, with your specific tools. Every skill is earned, not assumed. No duplicates, no bloat, no guesswork.

**Why am I doing this when AI can do it for me?** That's how Skilltrace was born.

## The Idea

Skilltrace is a silent assistant that works alongside you. It doesn't interrupt. It doesn't pollute your context. It doesn't ask questions.

While you focus on your project, Skilltrace runs in the background:

- **Observes** your conversations and tool usage across sessions
- **Detects** when meaningful, reproducible work is completed
- **Generates** specific, self-contained skills with exact steps, commands, and file paths
- **Versions** skills automatically when your approach evolves
- **Organizes** everything by project, searchable and ready to replay

You work. It learns. Your effort compounds.

## Why It Matters

- **Stop reinventing the wheel.** What you build once becomes a reusable recipe forever.
- **Cut costs.** Skills let Claude replay proven approaches in seconds instead of reasoning from scratch every session.
- **Share knowledge.** Skills are portable files. Drop them in a shared folder and your entire team benefits.
- **Never start from zero.** Every project feeds your skill library. The more you use Claude, the faster it gets.

## Install

Available from the [devstuff marketplace](https://github.com/Lover0ne/devstuff):

```bash
/plugin marketplace add Lover0ne/devstuff
/plugin install skilltrace@devstuff
```

That's it. Skilltrace activates on your next session. On first run, it introduces itself and asks if you want to enable tracking for the current project.

## How It Works

| When | What happens |
|------|-------------|
| Session starts | Skilltrace activates silently via hook |
| You work normally | Code, debug, build, deploy. No interruptions |
| After each prompt | Background agent evaluates if meaningful work was completed |
| Skill-worthy task detected | A skill is generated and stored in `.claude/skills/` |
| Session ends | Final check to make sure nothing was missed |

No configuration. No context pollution. No extra prompts. Just work.

## Features

- **Zero overhead.** Runs via hooks, never touches your main conversation.
- **Per-project tracking.** Opt-in per directory. Each project gets its own skill library.
- **Smart versioning.** Skills evolve with your approach. Old versions are archived, not lost.
- **Specific skills.** Not "how to set up auth" but "setting up NextJS auth with Clerk and Drizzle ORM".
- **Self-contained.** Every skill is a complete recipe, replayable with zero prior context.
- **Skill inventory.** Browse, search, and inspect all skills across projects.
- **Pause/resume.** Disable tracking anytime with `/skilltrace-pause`.
- **Cross-platform.** Works on macOS, Linux, and Windows.

## Commands

| Command | What it does |
|---------|-------------|
| `/skilltrace-dashboard` | Open the interactive skill dashboard in your browser |
| `/skilltrace-pause` | Pause activity tracking |
| `/skilltrace-resume` | Resume activity tracking |

You can also ask Claude in natural language: "open the skilltrace dashboard", "pause skilltrace", "resume tracking".

Additional commands are available for advanced use (`skilltrace-skills`, `skilltrace-overview`, `skilltrace-history`, `skilltrace-status`, `skilltrace-reindex`, `skilltrace-init`, `skilltrace-skip`).

## Project Structure

```
skilltrace/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── hooks/
│   ├── hooks.json           # Hook definitions (SessionStart, UserPromptSubmit, PreToolUse, SessionEnd)
│   ├── gate.sh              # PreToolUse gate (init check + task boundary)
│   └── wrapper.sh           # Cross-platform dispatcher
├── src/
│   ├── cli.py               # CLI entry point
│   ├── config.py            # Enable/disable, configuration
│   ├── registry.py          # Skill registry CRUD
│   ├── shared.py            # Atomic file ops, project ID management
│   ├── skill_ops.py         # Skill creation, versioning, archiving
│   └── transcript.py        # Session transcript scraper
├── agents/
│   └── skilltracer.md       # Background agent that evaluates and generates skills
├── commands/                 # Slash commands (init, skip, status, skills, overview, history, pause, resume, dashboard, reindex)
└── skills/
    └── skilltrace-manage/    # Built-in skill for managing generated skills
```

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Python 3.10+

## Support

If you'd like to go the extra mile, <a href="https://paypal.me/LorenzoCampagna"><strong>buy my dogs some treats</strong></a> 🐶

## License

MIT

---

*Stop writing skills. Start working. Let Skilltrace handle the rest.*

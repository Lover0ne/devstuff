<p align="center">
  <img width="512" height="279" alt="Skilltrace" src="https://github.com/user-attachments/assets/16f42d7f-9701-453c-b84b-a48a22ab4f19" />
</p>

<h1 align="center">Skilltrace</h1>

<p align="center"><strong>Designed for <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a></strong></p>

<p align="center"><strong>Your work becomes reusable. Automatically.</strong></p>

<p align="center"><a href="https://www-skilltrace.vercel.app/">Visit the official website</a></p>

---

## Why I built this

I'm lazy. Not the bad kind of lazy, the kind that hates doing the same thing twice. I think that's what drives most of us to code in the first place: if I can automate it, I will.

But here's what kept happening. I'd spend an hour setting up auth, configuring a deploy pipeline, wiring up an MCP server. Real work, good work. Then the session would end and all of that knowledge would just vanish. Next time I needed the same thing, I'd start over. Same research, same trial and error, same cost.

I knew the answer was skills. Write down what you did, step by step, so Claude can replay it next time. But writing a skill means stopping what you're doing, reflecting on every step, structuring it into a file, making it generic enough to reuse. It's a second job on top of the actual job. And I'm too lazy for that.

So I thought: why am I doing this manually when AI is right here?

That's how Skilltrace was born. A plugin that watches you work, figures out what's worth keeping, and writes the skill for you. You never stop working, you never write documentation, you never think about it. Your effort just compounds on its own.

## What it does

Skilltrace is a silent background assistant. It doesn't interrupt you, doesn't pollute your context, doesn't ask questions.

While you focus on your project, it:

- **Watches** what you build across sessions
- **Detects** when something meaningful and reproducible is completed
- **Generates** a self-contained skill with exact steps, commands, and file references
- **Versions** skills automatically when your approach evolves
- **Organizes** everything per project, browsable through a visual dashboard

You work. It learns. That's it.

## Why it matters

Every time you solve a problem, that solution either gets captured or gets lost. Most of the time it gets lost because nobody has time to document it.

Skilltrace changes that equation. Your work becomes a growing library of recipes that Claude can replay instantly. No reasoning from scratch, no re-discovering solutions, no wasted tokens repeating what you already figured out.

And because skills are just files, you can share them. Drop a skill in a shared folder and your whole team gets the benefit of what one person figured out once.

## Install

Available from the [devstuff marketplace](https://github.com/Lover0ne/devstuff):

```bash
/plugin marketplace add Lover0ne/devstuff
/plugin install skilltrace@devstuff
```

That's it. On your next session, Skilltrace introduces itself and asks if you want to enable tracking. Say yes and forget about it.

## How it works

| When | What happens |
|------|-------------|
| Session starts | Skilltrace activates silently |
| You work normally | Code, debug, build, deploy. No interruptions |
| After each task | A background agent evaluates what was done |
| Something worth keeping | A skill is generated in `.claude/skills/` |
| Session ends | Final check to make sure nothing was missed |

No configuration. No context pollution. No extra prompts.

## Features

- **Zero overhead.** Runs via hooks in the background. Your main conversation stays clean.
- **Per-project.** Each project has its own skill library. No cross-contamination.
- **Smart versioning.** Skills evolve with your approach. Old versions are archived, never lost.
- **Specific, not generic.** Not "how to set up auth" but "setting up NextJS auth with Clerk and Drizzle ORM".
- **Self-contained.** Every skill is a complete recipe anyone can follow from scratch.
- **Visual dashboard.** Browse all projects, skills, versions, and diffs in your browser.
- **Pause anytime.** `/skilltrace-pause` to stop, `/skilltrace-resume` to restart.
- **Cross-platform.** macOS, Linux, Windows.

## Commands

| Command | What it does |
|---------|-------------|
| `/skilltrace-dashboard` | Open the interactive dashboard in your browser |
| `/skilltrace-pause` | Pause tracking for this project |
| `/skilltrace-resume` | Resume tracking |

You can also just ask Claude: "open the skilltrace dashboard", "pause skilltrace", "resume tracking".

More commands are available for advanced use (`skilltrace-skills`, `skilltrace-overview`, `skilltrace-history`, `skilltrace-status`, `skilltrace-reindex`).

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Python 3.10+

## Support

If you'd like to go the extra mile, <a href="https://paypal.me/LorenzoCampagna"><strong>buy my dogs some treats</strong></a> 🐶

## License

MIT

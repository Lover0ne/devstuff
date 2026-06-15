<p align="center">
  <img width="512" height="279" alt="Skilltrace" src="https://github.com/user-attachments/assets/16f42d7f-9701-453c-b84b-a48a22ab4f19" />
</p>

<h1 align="center">Skilltrace</h1>

<p align="center"><strong>Designed for <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a></strong></p>

<p align="center"><strong>Your work becomes reusable. Automatically.</strong></p>

<p align="center"><a href="https://www-skilltrace.vercel.app/">Visit the official website</a></p>

---

## Why I built this

I'm lazy. Not the bad kind of lazy, the kind that hates doing the same thing twice. I think that's actually what drives most of us to code in the first place: if I can automate it, I will.

But here's what kept happening. I'd spend an hour setting up auth, configuring a deploy pipeline, wiring up an MCP server. Real work, good work. Then the session would end and all of that knowledge would just vanish. Next time I needed the same thing, I'd start over. Same research, same trial and error, same cost.

I knew the answer was skills. Write down what you did, step by step, so Claude can replay it next time. But writing a skill means stopping what you're doing, reflecting on every step, structuring it into a file, making it generic enough to reuse. It's a second job on top of the actual job. And I'm too lazy for that.

I also looked at what other plugins were doing. Most of them ship with dozens of commands that nobody remembers, overcomplicated backend servers just to manage a few utilities, and so many built-in skills that your agent drowns in noise instead of getting smarter. Your context window fills up with stuff you never asked for, and the model starts hallucinating because it's got too many conflicting instructions competing for attention.

So I thought: why am I doing this manually when AI is right here? And why does it have to be this complicated?

That's how Skilltrace was born. A plugin that watches you work, figures out what's worth keeping, and writes the skill for you. No server, no backend, no config files. You never stop working, you never document anything by hand, you never think about it. Your effort just compounds on its own.

## How it works

The key idea behind Skilltrace is simple: **it never touches your current task.** It always operates on the *previous* one.

When you send a new prompt, Skilltrace looks at what you just finished and evaluates it in the background. This means it never slows you down, never injects noise into your current conversation, never wastes tokens on tracking while you're in the middle of a critical task where you need your context clean, your agent sharp, and every token focused on the problem in front of you. Your context is sacred. Skilltrace doesn't touch it.

A background agent handles everything: it reads what happened, decides if it's worth a skill, writes it, and disappears. You don't see it, you don't interact with it, you don't even know it ran. If it decides the previous task was just a quick question or a formatting tweak, it does nothing.

| When | What happens |
|------|-------------|
| Session starts | Skilltrace hooks activate: SessionStart creates directories and prints a welcome, PreToolUse gate checks whether the project has been initialized |
| You work normally | Code, debug, build, deploy. No interruptions |
| You send a new prompt | UserPromptSubmit arms the task boundary; on the next tool use, the gate triggers a background evaluation of the *previous* task |
| Something worth keeping | A skill is generated in `.claude/skills/` within the project |
| Session ends | SessionEnd triggers a final evaluation pass so the last task isn't missed |

No configuration. No context pollution. No extra prompts.

## Architecture

Skilltrace is built on four interlocking pieces. You never interact with any of them directly, but here's what's happening under the hood.

**Gate system.** A PreToolUse hook (`gate.sh`) runs a three-stage check before every tool call. Stage 0: if the call is from a spawned subagent, let it through (subagents bypass the gate entirely). Stage 1: if the project hasn't been initialized yet (no `.skilltrace` marker), block the tool and prompt you to init or skip. Stage 2: if a task boundary has been armed, block once to force Claude to spawn the skilltracer agent before continuing. The gate uses atomic file moves to prevent races in concurrent sessions.

**Skilltracer agent.** A background agent (`agents/skilltracer.md`) that Claude spawns after every task boundary. It always scrapes the transcript independently rather than trusting the main conversation's summary. Its procedure: list existing project skills, scrape the transcript for what just happened, match that work against known skills, then create or version skills as needed. It also handles skill-derived work: if you invoked an existing skill, it evaluates whether the output was a faithful reproduction, a specialization, or an improvement.

**Transcript scraper.** Boundary-aware: it reads Claude Code's JSONL transcripts windowed to the previous prompt cycle, using the `last_traced_boundary` stored in the `.skilltrace` marker. When consecutive prompts skip evaluation, the window expands to cover the missed work. It captures subagent and workflow actions, records up to five parameters for MCP tool calls, redacts secrets, and filters out Skilltrace's own internal tool calls.

**Per-project storage.** Everything lives inside the project, not in your home directory. Skills go to `{project}/.claude/skills/{skill-id}/SKILL.md`. Versions are archived in `{project}/.claude/skilltrace/versions/{skill-id}/v{n}.md`. The registry at `{project}/.claude/skilltrace/registry.json` indexes all skills. The only global file is `~/.claude/skilltrace/config.json` for cross-project preferences.

## What makes it different

- **Not invasive.** Your conversation context is yours. Skilltrace runs entirely in the background through hooks. It doesn't add messages to your chat, doesn't consume tokens from your main conversation, doesn't make the model hallucinate by injecting competing instructions. It's invisible.
- **No server, no backend.** Everything is deterministic Python scripts and static files. No localhost server running, no ports to manage, no processes to babysit. Install it and forget it.
- **Per-project, not global.** Each project has its own skill library in `.claude/skills/`. Skills from your API project don't pollute your frontend project. No cross-contamination.
- **Smart versioning.** Skills evolve with your approach. When you improve how you deploy, Skilltrace updates the skill. Old versions are archived, never lost.
- **Specific, not generic.** Not "how to set up auth" but "setting up NextJS auth with Clerk and Drizzle ORM". Real stack, real tools, real steps.
- **Worktree-aware.** Works transparently when you use Claude Code worktrees. The gate resolves the project root from the original directory, so skills are always stored in the right place regardless of which worktree you're working in.
- **Cross-platform.** macOS, Linux, Windows.

## The dashboard

I wanted a way to see all my skills at a glance without digging through folders. So I built a dashboard that generates a self-contained HTML page you can open in any browser.

It shows every project, every skill, every version. You can browse history, compare versions side by side, search by name or tag, switch between light and dark mode. It's all generated on the fly from your local data with zero external dependencies.

Just say "open the skilltrace dashboard" or run `/skilltrace-dashboard`.

<p align="center">
  <img width="100%" alt="Dashboard overview" src="https://www-skilltrace.vercel.app/screenshots/dashboard-overview.png" />
</p>

<details>
<summary>Skill viewer</summary>
<p align="center">
  <img width="100%" alt="Skill viewer" src="https://www-skilltrace.vercel.app/screenshots/dashboard-skill-viewer.png" />
</p>
</details>

<details>
<summary>Version timeline</summary>
<p align="center">
  <img width="100%" alt="Version history" src="https://www-skilltrace.vercel.app/screenshots/dashboard-history.png" />
</p>
</details>

<details>
<summary>Version compare</summary>
<p align="center">
  <img width="100%" alt="Side-by-side diff" src="https://www-skilltrace.vercel.app/screenshots/dashboard-compare.png" />
</p>
</details>

<details>
<summary>Mobile</summary>
<p align="center">
  <img width="300" alt="Mobile view" src="https://www-skilltrace.vercel.app/screenshots/dashboard-mobile.png" />
</p>
</details>

## Install

Available from the [devstuff marketplace](https://github.com/Lover0ne/devstuff):

```bash
/plugin marketplace add Lover0ne/devstuff
/plugin install skilltrace@devstuff
```

Two commands and you're done. On your next session, Skilltrace introduces itself and asks if you want to enable tracking. Say yes and forget about it.

## Commands

| Command | What it does |
|---------|-------------|
| `/skilltrace-dashboard` | Open the interactive dashboard in your browser |
| `/skilltrace-start` | Enable or resume tracking for this project |
| `/skilltrace-stop` | Stop/pause tracking for this project |
| `/skilltrace-skills` | List all skills grouped by project, with status |
| `/skilltrace-history` | Show version history of a specific skill |
| `/skilltrace-reindex` | Rebuild registry from SKILL.md files on disk |

You can also just ask Claude in plain English: "open the skilltrace dashboard", "stop skilltrace", "list my skills".

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Python 3.10+

## Support

If you'd like to go the extra mile, <a href="https://paypal.me/LorenzoCampagna"><strong>buy my dogs some treats</strong></a> 🐶

## License

MIT

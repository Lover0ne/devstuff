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
| Session starts | Skilltrace activates silently |
| You work normally | Code, debug, build, deploy. No interruptions |
| You send a new prompt | Background agent evaluates the *previous* task |
| Something worth keeping | A skill is generated in `.claude/skills/` |
| Session ends | Final check to make sure the last task wasn't missed |

No configuration. No context pollution. No extra prompts.

## What makes it different

- **Not invasive.** Your conversation context is yours. Skilltrace runs entirely in the background through hooks. It doesn't add messages to your chat, doesn't consume tokens from your main conversation, doesn't make the model hallucinate by injecting competing instructions. It's invisible.
- **No server, no backend.** Everything is deterministic Python scripts and static files. No localhost server running, no ports to manage, no processes to babysit. Install it and forget it.
- **Per-project, not global.** Each project has its own skill library in `.claude/skills/`. Skills from your API project don't pollute your frontend project. No cross-contamination.
- **Smart versioning.** Skills evolve with your approach. When you improve how you deploy, Skilltrace updates the skill. Old versions are archived, never lost.
- **Specific, not generic.** Not "how to set up auth" but "setting up NextJS auth with Clerk and Drizzle ORM". Real stack, real tools, real steps.
- **Pause anytime.** Don't want tracking on a specific project? `/skilltrace-pause`. Want it back? `/skilltrace-resume`. Per project, not global.
- **Three commands to learn.** Dashboard, pause, resume. Everything else is automatic or available through natural language.
- **Cross-platform.** macOS, Linux, Windows.

## The dashboard

I wanted a way to see all my skills at a glance without digging through folders. So I built a dashboard that generates a self-contained HTML page you can open in any browser.

It shows every project, every skill, every version. You can browse history, compare versions side by side, search by name or tag, switch between light and dark mode. It's all generated on the fly from your local data with zero external dependencies.

Just say "open the skilltrace dashboard" or run `/skilltrace-dashboard`.

<p align="center">
  <img width="100%" alt="Dashboard light mode" src="https://www-skilltrace.vercel.app/screenshots/dashboard-light.png" />
</p>

<details>
<summary>Dark mode</summary>
<p align="center">
  <img width="100%" alt="Dashboard dark mode" src="https://www-skilltrace.vercel.app/screenshots/dashboard-dark.png" />
</p>
</details>

<details>
<summary>Skill viewer with version history</summary>
<p align="center">
  <img width="100%" alt="Skill modal" src="https://www-skilltrace.vercel.app/screenshots/dashboard-modal.png" />
</p>
</details>

<details>
<summary>Side-by-side diff</summary>
<p align="center">
  <img width="100%" alt="Version compare" src="https://www-skilltrace.vercel.app/screenshots/dashboard-compare.png" />
</p>
</details>

<details>
<summary>Mobile</summary>
<p align="center">
  <img width="300" alt="Mobile view" src="https://www-skilltrace.vercel.app/screenshots/dashboard-mobile.png" />
  <img width="300" alt="Mobile menu" src="https://www-skilltrace.vercel.app/screenshots/dashboard-mobile-menu.png" />
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
| `/skilltrace-pause` | Pause tracking for this project |
| `/skilltrace-resume` | Resume tracking |

You can also just ask Claude in plain English: "open the skilltrace dashboard", "pause skilltrace", "resume tracking".

More commands are available for advanced use (`skilltrace-skills`, `skilltrace-overview`, `skilltrace-history`, `skilltrace-status`, `skilltrace-reindex`).

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Python 3.10+

## Support

If you'd like to go the extra mile, <a href="https://paypal.me/LorenzoCampagna"><strong>buy my dogs some treats</strong></a> 🐶

## License

MIT

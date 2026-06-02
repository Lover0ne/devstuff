<h1 align="center">Copycat</h1>

<p align="center"><strong>Designed for <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a></strong></p>

<p align="center"><strong>Turn any skill into a reusable template. Instantly.</strong></p>

---

## Why I built this

I had a skill that set up auth perfectly for one of my projects. Clerk, Drizzle, NextJS, the whole thing. Step by step, every command, every config. It worked great.

Then a friend asked me to share it. And I realized I couldn't. The skill was full of my paths, my API keys, my project name, my repo URL. Sharing it meant either leaking all of that or spending twenty minutes reading every line and replacing values by hand. And if I missed one, I'd just handed someone my credentials.

So I built Copycat. Point it at any skill and it strips out everything project-specific: paths, names, URLs, keys, emails, domains. It replaces them with smart `{{placeholders}}` that describe what each value is. The result is a clean, portable template that anyone can use without knowing anything about the original project.

## How it works

```
/copycat-clone my-deploy-skill
```

Copycat asks you one question: do you want a raw template or a questionnaire? Then it:

1. Finds the skill
2. Reads every line and identifies project-specific values
3. Replaces them with descriptive `{{placeholders}}`
4. Saves the result as a new skill

That's it. Two modes:

| Mode | What you get | Best for |
|------|-------------|----------|
| **Sanitize only** | Raw `{{placeholders}}` with a reference table | Sharing, auditing, manual editing |
| **Questionnaire** | Adds a setup section that asks the user for every value before running | Templates that others can invoke directly |

## Placeholder rules

Copycat is smart about how it replaces values:

- **Same value, same role:** one placeholder, asked once. If `myapp` appears 15 times as the project name, it becomes `{{project_name}}` everywhere.
- **Same type, different role:** separate placeholders. A sender email and recipient email become `{{email_from}}` and `{{email_to}}`.
- **Nested paths:** `/Users/me/projects/myapp/src` becomes `{{project_dir}}/{{project_name}}/src`. Only the variable parts change.
- **Never touched:** tool names, frameworks, standard commands, language keywords. Those stay exactly as they are.

## Install

Available from the [devstuff marketplace](https://github.com/Lover0ne/devstuff):

```bash
/plugin marketplace add Lover0ne/devstuff
/plugin install copycat@devstuff
```

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI

## License

MIT

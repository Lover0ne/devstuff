<h1 align="center">Copycat</h1>

<p align="center"><strong>Designed for <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a></strong></p>

<p align="center"><strong>Turn any skill into a reusable template. Instantly.</strong></p>

Copycat is a Claude Code plugin that takes any skill and strips out every project-specific value (paths, names, URLs, keys, emails, you name it) and replaces them with smart `{{placeholders}}`. The result is a portable template anyone can use.

---

## The Problem

Skills are powerful, but they're born specific. A skill that deploys *your* app to *your* server with *your* API keys is useless to anyone else, and honestly risky to share. Manually sanitizing a skill means reading every line, spotting every hardcoded value, and replacing them consistently. Miss one and you've leaked a path, a name, or worse.

## The Solution

One command. Copycat reads the skill, identifies every project-specific value, and replaces them with descriptive placeholders. You pick the output format: a sanitized template for manual use, or a full questionnaire that collects inputs automatically.

## Install

Available from the [devstuff marketplace](https://github.com/Lover0ne/devstuff):

```bash
/plugin marketplace add Lover0ne/devstuff
/plugin install copycat@devstuff
```

## Usage

```
/copycat:clone <skill-name>
```

Copycat will:

1. **Ask** which mode you want: **sanitize only** or **questionnaire**
2. **Find** the skill in your project or installed plugins
3. **Analyze** it for project-specific values (paths, names, URLs, secrets, etc.)
4. **Replace** each value with a descriptive `{{placeholder}}`
5. **Save** the template as `<skill-name>-copycat`

### Modes

| Mode | What you get | Best for |
|------|-------------|----------|
| **Sanitize only** | Raw `{{placeholders}}` with a reference table | Sharing, auditing, manual editing |
| **Questionnaire** | Setup section that collects values via `AskUserQuestion` | Reusable templates others invoke directly |

### Example

```
/copycat:clone my-deploy-skill
```

Produces a `my-deploy-skill-copycat` skill where `/Users/me/myapp` becomes `{{project_dir}}` and `acme-api.com` becomes `{{api_domain}}`.

## Placeholder Rules

- **Same value, same role:** single placeholder, asked once.
- **Same type, different role:** separate placeholders (e.g. `{{email_from}}` vs `{{email_to}}`).
- **Nested composition:** `/Users/me/projects/myapp/src` becomes `{{project_dir}}/{{project_name}}/src`.
- **Never anonymized:** tool names, frameworks, standard commands, and language keywords stay as-is.

## Project Structure

```
copycat/
├── .claude-plugin/
│   └── plugin.json       # Plugin manifest
├── commands/
│   └── clone.md          # /copycat:clone command
└── skills/
    └── .gitkeep
```

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI

## License

MIT

---

*Share skills without sharing secrets.*

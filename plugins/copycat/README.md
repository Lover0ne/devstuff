# Copycat

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin that turns any skill into a reusable template.

Point it at a skill, and Copycat replaces every project-specific value — paths, names, URLs, keys, emails — with smart `{{placeholders}}`. You choose the output format: sanitized-only or full questionnaire.

## Install

```
/install-plugin https://github.com/Lover0ne/copycat
```

## Usage

```
/copycat:clone <skill-name>
```

Copycat will:

1. **Ask** which mode you want: **sanitize only** or **questionnaire**
2. **Find** the skill in `~/.claude/skills/` or installed plugins
3. **Analyze** it for project-specific values (paths, names, URLs, secrets, etc.)
4. **Replace** each value with a descriptive `{{placeholder}}`
5. **Output** based on your chosen mode:
   - **Sanitize only** — raw `{{placeholders}}` with a reference table. Good for sharing, auditing, or manual editing.
   - **Questionnaire** — adds a setup section that collects every value via `AskUserQuestion` before execution. Good for reusable templates others can invoke directly.
6. **Save** the template as `<skill-name>-copycat`

### Example

```
/copycat:clone my-deploy-skill
```

Produces a `my-deploy-skill-copycat` skill where hardcoded values like `/Users/me/myapp` become `{{project_dir}}` and `acme-api.com` becomes `{{api_domain}}`.

## Placeholder rules

- **Same value, same role** → single placeholder, asked once
- **Same type, different role** → separate placeholders (e.g. `{{email_from}}` vs `{{email_to}}`)
- **Nested composition** → `/Users/me/projects/myapp/src` becomes `{{project_dir}}/{{project_name}}/src`
- **Never anonymized** → tool names, frameworks, standard commands, language keywords

## License

MIT

# Copycat

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin that turns any skill into a reusable template.

Point it at a skill, and Copycat replaces every project-specific value — paths, names, URLs, keys, emails — with smart `{{placeholders}}`. The output is a new skill that asks users for their own values before running.

## Install

```
/install-plugin https://github.com/Lover0ne/copycat
```

## Usage

```
/copycat:clone <skill-name>
```

Copycat will:

1. **Find** the skill in `~/.claude/skills/` or installed plugins
2. **Analyze** it for project-specific values (paths, names, URLs, secrets, etc.)
3. **Replace** each value with a descriptive `{{placeholder}}`
4. **Generate** a new skill with a setup section that collects inputs via `AskUserQuestion`
5. **Save** the template as `<skill-name>-copycat`

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

---
name: clone
description: Anonymize a skill into a reusable template with smart {{placeholders}}
---

# Clone & Anonymize a Skill

You received a skill name as argument. Follow these steps exactly.

## Step 1: Find the source skill

Search for the skill by name in these locations (stop at first match):
1. `~/.claude/skills/` — each subfolder contains a `SKILL.md`
2. Plugin skill directories — glob `~/.claude/plugins/cache/*/skills/*/SKILL.md`

Read the skill's `SKILL.md` content. If not found, tell the user and stop.

## Step 2: Analyze for project-specific values

Read the entire skill carefully. Identify ALL values that are specific to the original project/context and would need to change for reuse. Categories:

| Category | Examples | Placeholder style |
|---|---|---|
| File/directory paths | `/Users/me/myapp`, `C:\Projects\foo` | `{{project_dir}}`, `{{file_path}}` |
| Project/app names | `myapp`, `acme-api` | `{{project_name}}`, `{{app_name}}` |
| Organization/client names | `Acme Corp`, `client-x` | `{{org_name}}`, `{{client_name}}` |
| Email addresses | `john@acme.com` | `{{email_from}}`, `{{email_to}}` — role-aware! |
| API keys/tokens/secrets | `sk-abc123`, `Bearer xyz` | `{{api_key}}`, `{{auth_token}}` |
| URLs/endpoints | `https://api.acme.com/v1` | `{{api_base_url}}` |
| Hostnames/domains | `acme.com`, `staging.acme.io` | `{{domain}}`, `{{staging_domain}}` |
| Port numbers | `3000`, `8080` | `{{port}}` |
| Database/bucket/cluster names | `myapp-db`, `prod-bucket` | `{{db_name}}`, `{{bucket_name}}` |
| Config values | region, env-specific settings | `{{aws_region}}`, `{{environment}}` |
| Usernames/handles | `@johndoe`, `admin` | `{{username}}` |
| Repository names | `Lover0ne/myrepo` | `{{repo_owner}}/{{repo_name}}` |
| IP addresses / CIDRs | `192.168.1.10`, `10.0.0.0/24` | `{{server_ip}}`, `{{subnet_cidr}}` |
| Cloud resource IDs | `arn:aws:s3:::my-bucket`, `projects/my-gcp` | `{{aws_arn}}`, `{{gcp_project_id}}` |
| Docker image names | `acme/myapp:latest`, `registry.io/team/svc` | `{{docker_image}}`, `{{container_registry}}` |
| SSH keys / certificates | inline PEM blocks, `~/.ssh/id_rsa` | `{{ssh_key_path}}`, `{{certificate_path}}` |
| Team/channel names | `#deploy-alerts`, `@backend-team` | `{{slack_channel}}`, `{{team_name}}` |
| CI/CD pipeline names | `deploy-prod.yml`, `Jenkins::MyApp` | `{{pipeline_name}}`, `{{workflow_file}}` |
| Environment variable names | `MY_APP_DB_URL`, `ACME_SECRET_KEY` | `{{env_var_db}}`, `{{env_var_secret}}` |
| Password hashes / salts | `$2b$10$abc...`, inline bcrypt/argon2 | `{{password_hash}}` |

## Step 3: Smart placeholder rules

**CRITICAL — follow these rules exactly:**

1. **Same value, same role → one placeholder.** If `myapp` appears 15 times always meaning the project name, use `{{project_name}}` everywhere. Ask the user ONCE.

2. **Same type, different role → separate placeholders.** If the skill has a sender email (`from@x.com`) and recipient email (`to@y.com`), these are `{{email_from}}` and `{{email_to}}`. Two separate questions.

3. **Follow the process data flow.** If the skill describes an API that forwards from source to destination, `{{source_url}}` and `{{destination_url}}` are distinct even though both are URLs. Read the skill's logic to understand which values play different roles.

4. **Compose nested placeholders.** If a path is `/Users/me/projects/myapp/src/config.ts`, decompose: `{{project_dir}}/{{project_name}}/src/config.ts`. Only anonymize the variable parts, keep structural parts (`src/`, `config.ts`) if they're generic.

5. **Never anonymize:**
   - Tool names (Bash, Read, Write, npm, git, docker, etc.)
   - Framework/library names (Next.js, React, Express, etc.)
   - Standard commands and flags
   - Programming language keywords
   - Section headings, step numbers, structural markdown
   - Generic file extensions (`.ts`, `.py`, `.md`)

6. **Placeholder naming:** `{{snake_case}}`, descriptive, max 30 chars. Prefer specificity: `{{slack_webhook_url}}` over `{{url_2}}`.

## Step 4: Build the anonymized skill

Create the new SKILL.md with this structure:

```
---
name: {original-name}-copycat
description: "[Template] {original description with specific names replaced by generic terms}"
---

## Setup — Required Inputs

Before executing this skill, you MUST collect the following values from the user using AskUserQuestion.
Group related inputs into a single AskUserQuestion call when possible (max 4 questions per call).

| Placeholder | Description | Example |
|---|---|---|
| {{placeholder_1}} | Clear description of what this value is | realistic example |
| {{placeholder_2}} | Clear description of what this value is | realistic example |

After collecting ALL values, perform a **global find-and-replace** for each placeholder across the ENTIRE skill content below. Every `{{placeholder}}` instance MUST be replaced — if a placeholder appears 20 times, all 20 occurrences get the same user-provided value. Do NOT skip any occurrence. Then follow the skill steps below.

---

{Original skill content with all project-specific values replaced by {{placeholders}}}
```

**Important for the Setup section:**
- Order placeholders logically (project-level first, then detail-level)
- Description must be clear enough that someone unfamiliar with the original project can answer
- Example column shows a realistic but obviously fake value
- If there are more than 4 inputs, use multiple AskUserQuestion calls grouped by category

## Step 5: Write the anonymized skill

Write the file to: `${CLAUDE_PLUGIN_ROOT}/skills/{original-name}-copycat/SKILL.md`

Create the directory if it doesn't exist.

## Step 6: Confirm to user

Report:
- Source skill name and location
- Number of unique placeholders created
- List of placeholders with descriptions
- Output path
- How to invoke: `/copycat:{original-name}-copycat`

# OpenHands account skills

Account-level OpenHands skills and sub-agents. Registered as a personal marketplace with
`auto_load: true`, so these load at the start of every conversation.

## Layout

```
.agents/
  skills/          # Agent Skills (SKILL.md per folder) + path-triggered rules (*.md with `paths:`)
  agents/          # file-based sub-agents (*.md with YAML frontmatter)
.openhands/
  hooks.json       # lifecycle hooks (guard + quality gate)
  hooks/*.sh
```

## What is here

- 7 project-trap skills: conversation export, secret redaction, Playwright evidence QA,
  brand/i18n, strict typecheck gate, multi-session PR coordination, sandbox lifecycle.
- 16 role skills covering a full software company: execution OS, PRD, architecture/ADR,
  API design, migrations, testing, CI/CD, release, incident response, code review,
  performance, accessibility, security, supply chain, observability, privacy, git, docs.
- 3 path-triggered rules: workflow schedule claims, brand-vs-content, docs evidence format.
- 15 role sub-agents plus 4 project sub-agents.

## Registration

```bash
curl -X POST -H "Authorization: Bearer $OPENHANDS_API_KEY" -H "Content-Type: application/json" \
  -d '[{"name":"openhands-account","source":"github:madnessgate44-debug/Openhands","repo_path":".agents","auto_load":true}]' \
  https://app.all-hands.dev/api/v1/settings
```

Preview what a marketplace resolves to without starting a conversation:

```bash
curl -X POST -H "Authorization: Bearer $OPENHANDS_API_KEY" -H "Content-Type: application/json" \
  -d '[{"name":"openhands-account","source":"github:madnessgate44-debug/Openhands","repo_path":".agents"}]' \
  https://app.all-hands.dev/api/v1/skills/marketplace-skills
```

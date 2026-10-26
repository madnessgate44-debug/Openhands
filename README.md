# OpenHands account library

Account-level skills, sub-agents and lifecycle hooks for OpenHands, packaged as a
portable [Agent Plugins](https://agent-plugins.org) 1.0.0 package and registered as a personal
marketplace with `auto_load: true`, so every conversation picks them up.

## What is here

- **28 skills** — 25 keyword-triggered skills plus 3 path-triggered rules.
- **19 sub-agents** — a full software company plus project-specific roles.
- **2 lifecycle hooks** — a destructive-command guard (PreToolUse) and a quality gate (Stop).

## Layout

```
.agents/                      # the marketplace root (repo_path = ".agents")
  .plugin/marketplace.json    # marketplace manifest: declares one plugin
  plugin.json                 # Agent Plugins 1.0.0 manifest (the plugin itself)
  skills/<name>/SKILL.md      # 25 keyword-triggered skills (AgentSkills format)
  skills/<name>.md            # 3 path-triggered rules (frontmatter `paths:`)
  dev.openhands/
    agents/<name>.md          # 19 sub-agents
    hooks/hooks.json          # lifecycle hooks
    hooks/*.sh                # hook scripts
scripts/validate.py           # validates every manifest, frontmatter, skill and hook
```

Why the indirection: a marketplace on its own loads **only** skills. Sub-agents and hooks load
because the marketplace declares a plugin (`plugins: [{ source: "." }]`) and that plugin carries
them under `dev.openhands/`. Removing the plugin declaration silently drops 19 agents and 2 hooks.

## Components

| Component | Count | Loads because |
| - | - | - |
| Skills | 25 | `skills/<name>/SKILL.md`, keyword `triggers:` |
| Path rules | 3 | `skills/<name>.md`, `paths:` globs |
| Sub-agents | 19 | plugin → `dev.openhands/agents/*.md` |
| Hooks | 2 | plugin → `dev.openhands/hooks/hooks.json` |

## Registration

```bash
curl -X POST -H "Authorization: Bearer $OPENHANDS_API_KEY" -H "Content-Type: application/json" \
  -d '[{"name":"openhands-account","source":"github:madnessgate44-debug/Openhands","repo_path":".agents","auto_load":true}]' \
  https://app.all-hands.dev/api/v1/settings
```

## Validating a change

```bash
python3 scripts/validate.py
```

A single malformed file silently drops that component from the catalog, so run this before
committing. Start a new conversation afterwards for the catalog to rebuild.

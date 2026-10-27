# OpenHands account library

Account-level skills, sub-agents and lifecycle hooks for OpenHands, packaged as a
portable [Agent Plugins](https://agent-plugins.org) 1.0.0 package and registered as a personal
marketplace with `auto_load: true`, so every conversation picks them up.

## What is here

- **34 skills** — 31 keyword-triggered skills plus 3 path-triggered rules.
- **19 sub-agents** — a full software company plus project-specific roles.
- **2 lifecycle hooks** — a destructive-command guard (PreToolUse) and a quality gate (Stop).

## Layout

```
.agents/                      # the marketplace root (repo_path = ".agents")
  .plugin/marketplace.json    # marketplace manifest: declares one plugin
  plugin.json                 # Agent Plugins 1.0.0 manifest (the plugin itself)
  skills/<name>/SKILL.md      # 31 keyword-triggered skills (AgentSkills format)
  skills/<name>.md            # 3 path-triggered rules (frontmatter `paths:`)
  dev.openhands/
    agents/<name>.md          # 19 sub-agents
    hooks/hooks.json          # lifecycle hooks
    hooks/guard.py            # PreToolUse guard (decision logic)
    hooks/guard.sh            # PreToolUse guard (thin wrapper -> guard.py)
    hooks/quality_gate.sh     # Stop gate
scripts/validate.py           # validates every manifest, frontmatter, skill and hook
tests/hooks_test.sh           # exercises the guard and the quality gate
```

Why the indirection: a marketplace on its own loads **only** skills. Sub-agents and hooks load
because the marketplace declares a plugin (`plugins: [{ source: "." }]`) and that plugin carries
them under `dev.openhands/`. Removing the plugin declaration silently drops 19 agents and 2 hooks.

## Components

| Component | Count | Loads because |
| - | - | - |
| Skills | 31 | `skills/<name>/SKILL.md`, keyword `triggers:` |
| Path rules | 3 | `skills/<name>.md`, `paths:` globs |
| Sub-agents | 19 | plugin → `dev.openhands/agents/*.md` |
| Hooks | 2 | plugin → `dev.openhands/hooks/hooks.json` |

## Hooks

- **`pre_tool_use` → `guard.py`** denies destructive or secret-leaking terminal commands: force-push
  and push to `main`/`master` (including `HEAD:main`, `+ref` and `--all`/`--mirror`), `--no-verify`
  (any git subcommand) and `git commit -n`, `rm -rf` of `/`, `~`, `.git` or a top-level system dir,
  printing a secret variable (`echo $TOKEN` and any `*TOKEN*`/`*SECRET*`/`*PASSWORD*`/`*API_KEY*`
  name, bare `printenv`/`env`, `printenv <SECRET>`, `cat /proc/*/environ`, `cat .env*`), and
  `curl`/`wget` piped into a shell or an interpreter. It skips git global options (`-C`, `-c`,
  `--git-dir`, …), unwraps `bash -c`/`sudo`/`timeout`/`xargs`/`env`/`eval`/`$(…)`/backticks
  (depth 3), and splits the command into real argv tokens, so a branch name that merely contains
  `main` is not a false positive.
- **`stop` → `quality_gate.sh`** refuses to finish while `git diff --check` reports whitespace
  errors (in the worktree *and* in committed changes vs `origin/main`), or while a project
  typecheck fails. A loop breaker allows the stop after 3 consecutive denials and prints a warning,
  so a stuck agent is never trapped.

**What the guard is and is not.** The guard stops honest mistakes. It is not a security boundary:
it inspects one `terminal` command at a time, and a determined command can get around it (encoding,
indirection the tokenizer does not model, a tool other than `terminal`). Do not rely on it to
contain a hostile actor.

## Registration

```bash
curl -X POST -H "Authorization: Bearer $OPENHANDS_API_KEY" -H "Content-Type: application/json" \
  -d '[{"name":"openhands-account","source":"github:madnessgate44-debug/Openhands","repo_path":".agents","auto_load":true}]' \
  https://app.all-hands.dev/api/v1/settings
```

## Validating a change

```bash
python3 scripts/validate.py    # manifests, frontmatter, skills, sub-agents, hooks
bash tests/hooks_test.sh       # guard allow/deny cases and the quality-gate loop breaker
```

A single malformed file silently drops that component from the catalog, so run both before
committing. CI runs them on every pull request (`.github/workflows/validate.yml`). Start a new
conversation afterwards for the catalog to rebuild.

## Verified loading

Loaded from a fresh clone with `openhands-sdk` 1.58.2:

```
marketplace: openhands-account | plugins: ['account-library']
skills 34 agents 19 hooks ['post_tool_use', 'pre_tool_use', 'session_end', 'session_start', 'stop', 'user_prompt_submit']
```

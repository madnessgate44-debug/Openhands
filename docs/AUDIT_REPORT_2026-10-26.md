# Library audit and remediation — decision record

Date: 2026-10-26. Repository: `madnessgate44-debug/Openhands` (public, default branch `main`).
Scope: audit every skill, sub-agent, path rule and hook, then fix what was wrong.

## Method

Ground truth was established from three sources before any change:

1. The OpenHands SDK internals (`openhands-sdk` 1.58.2): the loader, format detection and the
   hook event schema.
2. The official docs (`docs.openhands.dev/sdk/guides/plugins`).
3. The reference repository `OpenHands/extensions`.

The loader model that came out of this, and that drives every decision below:

- A **marketplace loads only skills**. Sub-agents and hooks load **only** through a **plugin**.
- Canonical manifest: `.plugin/plugin.json` (Agent Plugins 1.0.0). Components: `skills/`,
  `hooks/hooks.json`, `agents/`.
- Format detection order: Agent Plugins first (root `plugin.json` with `$schema`), Claude Code
  last (universal fallback that infers a manifest from the directory name).
- `skills/*.md` with a `paths:` key load as path-triggered rules via the Claude Code format.
- `hooks.json` accepts flat snake_case event keys and a PascalCase `{"hooks": {...}}` wrapper.

Baseline (fresh clone, before changes): **28 skills, 19 sub-agents, 2 hooks** loaded.

## What was broken

1. **The guard hook did not work as intended.** `guard.sh` matched raw substrings of the command,
   so it could be bypassed (extra spaces, quoting) and produced false positives — any command
   containing the word `printenv`, including a `grep` for it, was denied. (This fired live during
   the audit: a command that merely mentioned `printenv` was blocked.)
2. **The quality gate could not fire on committed work.** It ran `git diff --check`, which sees only
   the working tree, so once changes were committed the gate passed vacuously. It also had no way
   out: a gate the agent could not satisfy would deny the stop forever.
3. **The `engineering-execution-os` skill could deadlock a session.** It instructed the agent to
   stop and report BLOCKED when the repository had no `ENGINEERING_EXECUTION_OS.md`, which is the
   common case.
4. **All 19 sub-agents were 4–6 bullet role prompts** (1,640 words total) with no inputs, outputs or
   definition of done.
5. **There was no automated validation.** `scripts/validate.py` existed but nothing ran it, and it
   did not check the things that silently drop a component (bad YAML, wrong tool name, unquoted
   numbers, plugin `skills:` wiring).

## What was done — one branch and one PR per group

| PR | Branch | Change |
| - | - | - |
| #1 (draft) | `audit/pr1-hooks-and-blockers` | Rewrote the guard (`guard.py`, JSON + argv tokens), added the quality-gate loop breaker and committed-diff check, de-blocked `engineering-execution-os`, added `tests/hooks_test.sh` (38 cases). |
| #2 | `audit/pr2-validation-ci` | Added `.github/workflows/validate.yml` (free) and strengthened `scripts/validate.py`. |
| #3 | `audit/pr3-structure-and-content` | Deepened all 19 sub-agents to a consistent Inputs/Method/Output/Definition-of-done shape (1,640 → 3,115 words). |
| #4 | `audit/pr4-docs` | Documented the hooks, the tests and CI in `README.md` and `AGENTS.md`. |
| #5 | `audit/pr5-report` | This record. |

No branch was pushed to `main`.

## Decisions made without asking (owner was offline)

1. **Kept the Agent Plugins layout** (root `plugin.json` + `dev.openhands/`). The owner confirmed
   this is the path the plugin loads. An earlier migration I had started toward `.plugin/` was
   reverted before pushing.
2. **Made `guard.sh` a thin wrapper around `guard.py`** rather than deleting it, so any existing
   `bash guard.sh` invocation keeps working.
3. **Did not split any skill.** The largest `SKILL.md` is 329 words, well under the 3,000-word
   guideline, so no `references/` extraction was warranted.
4. **Did not move `amina-brand-and-i18n` out of this library.** It is deliberately account-level so
   the same session can use it across the app and its docs; moving it to the app repo would remove
   it from account-level sessions.
5. **Merge order matters.** The CI workflow lives in PR #2, so PR #1, #3 and #4 have no checks until
   #2 is merged (or their branches are rebased onto it). Recommended order: **#2 → #1 → #3 → #4**,
   then mark #1 ready. PR #1 is a draft pending exactly this.
6. **`quality_gate.sh` only enforces gates that exist.** It runs a typecheck only if `package.json`
   defines a `typecheck` script, so the hook never blocks on absent tooling.

## Evidence

All commands below were run for real; output is verbatim.

### Fresh-clone load (SDK `openhands-sdk` 1.58.2)

```
marketplace: openhands-account | plugins: ['account-library']
skills 28 agents 19 hooks ['post_tool_use', 'pre_tool_use', 'session_end', 'session_start', 'stop', 'user_prompt_submit']
```

### `python3 scripts/validate.py` (PR #2 version) → exit 0

```
skills: 28  sub-agents: 19  hooks: 2
OK: manifests, frontmatter, skills, sub-agents and hooks are valid
```

Deliberate-violation test (renamed the `api-design` skill and added `count: 502`) → exit 1:

```
skills: 28  sub-agents: 19  hooks: 2

2 FAILURE(S):
  - .agents/skills/api-design/SKILL.md: unquoted numeric value for 'count' ('502'); quote it
  - .agents/skills/api-design/SKILL.md: name 'wrong-name' != 'api-design'
```

### `bash tests/hooks_test.sh` (PR #1) → exit 0

```
TOTAL: 38 passed, 0 failed
```

Full case list (allow and deny) is in the PR #1 body.

### CI

PR #2 workflow `Validate library` → `validate` check **pass** (9s),
run 40431891698. PRs #1, #3, #4 show no checks because the workflow is introduced by #2 (see
decision 5).

## Verified / not verified

- **Verified:** baseline load counts; the guard and gate behaviour (direct invocation, 38 cases);
  `validate.py` catching real violations; PR #2 CI green; the deepened agents load with their full
  bodies.
- **Not verified:** end-to-end hook enforcement through the live marketplace loader in a *new*
  conversation. The hook contract is exercised directly (stdin JSON → exit code + stdout JSON),
  which is the same contract the executor uses, but a fresh-conversation run was not performed.
  PR #2's CI and a fresh-conversation check are the remaining confirmation.

## Remaining work (not in scope for this round)

- Mark PR #1 ready once #2 has merged and its own CI is green.
- A fresh-conversation check that the guard and gate fire through the loader.

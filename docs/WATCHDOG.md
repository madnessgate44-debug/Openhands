# Loop watchdog

Everything in the loop — the hooks, the backlog gate, the loop skill — runs **inside** an
OpenHands conversation, so it dies with that conversation.

On 2026-10-30 that happened. A nine-hour run stopped after 46 minutes: the model proxy
returned an HTML "Service Temporarily Unavailable" page, OpenHands set
`execution_status=error`, and nothing restarted it. Nothing ran for 14 hours. The
conversation's own retries (`num_retries=5`) never fired, because the failure was outside
the conversation's control.

The watchdog lives outside. It is a GitHub Action, so it keeps running when the
conversation does not.

## What it does

Every 30 minutes (`.github/workflows/watchdog.yml`, cron `*/30 * * * *`):

1. Read `docs/STATUS.md` and `docs/BACKLOG.md`.
2. Ask: is there unfinished work? A declared `BLOCKER` other than `none` means the loop is
   deliberately paused, so that is *not* work. Otherwise: an unchecked `status=ready`
   backlog line, or a `Next:` line that is not `none`, counts as work.
3. Ask: has anything happened in the last 45 minutes? It looks at the newest of: a commit
   on `main`, a PR update, an issue/PR comment, and — as a second signal — whether any
   OpenHands conversation is still active.
4. If there is work, nothing is active, and nothing has happened for 45 minutes, start a
   **new** OpenHands conversation that resumes from `docs/STATUS.md`.

## Guardrails

All four are enforced in `scripts/watchdog.py`, not in a conversation, so they hold even if
the conversation is broken.

| Guardrail | Behaviour |
|---|---|
| One run at a time | Skips if any OpenHands conversation has `execution_status` `running` or `waiting`. |
| Restart budget | At most 6 restarts per rolling 24h, counted by conversation title. |
| Kill switch | A file at `docs/WATCHDOG_OFF` stops it outright. |
| Logging | Every restart is appended to `docs/STATUS.md` as a `Last 5 actions` line, plus a commit. |

It **fails open**: if it cannot read GitHub or OpenHands, it logs why and exits 0 without
restarting. A watchdog that stops the loop is worse than one that misses a restart.

## Enabling it

The workflow needs one repository secret:

- `OPENHANDS_API_KEY` — the key the watchdog uses to start a conversation.
  `GITHUB_TOKEN` is supplied by Actions automatically.

Without it the watchdog logs a message and exits 0; it never fails the build.

## Turning it off

Two ways, both reversible:

- Create `docs/WATCHDOG_OFF` (any content). The workflow checks for it and skips the run.
  Delete the file to resume.
- Disable the **Loop watchdog** workflow in the repository's Actions tab.

## Cost

$0. It uses the existing OpenHands key and GitHub Actions, no card and no paid service. The
watchdog does no LLM work itself — it only starts a conversation, which is the same
mechanism the existing `Openhands loop` automation already uses.

## Testing it

```bash
bash tests/watchdog_test.sh                 # 24 cases: guardrails, staleness, logging
WATCHDOG_DRY_RUN=1 python3 scripts/watchdog.py   # decide without starting anything
```

The dry run prints the decision and the reason, and starts nothing.

## Note on the schedule

A `schedule:` trigger only runs on the **default branch**. Until this file is on `main`, the
cron does nothing. Verify a real scheduled run with:

```bash
curl -s "https://api.github.com/repos/madnessgate44-debug/Openhands/actions/runs?event=schedule" \
  -H "Authorization: Bearer $GITHUB_TOKEN"
```

A written cadence is not a scheduler; check the API before claiming a run happened.

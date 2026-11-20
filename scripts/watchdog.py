#!/usr/bin/env python3
"""Out-of-conversation watchdog for the self-driving loop.

The hooks, the backlog gate and the loop skill all run *inside* an OpenHands
conversation, so they die with it. On 2026-10-30 a nine-hour run stopped after
46 minutes: the model proxy returned an HTML "Service Temporarily Unavailable"
page, OpenHands set execution_status=error, and nothing restarted the loop.

This watchdog runs on a GitHub Action cron, outside that boundary. Each run it
answers one question: is the loop stalled while work remains? If yes, and the
guardrails allow it, it starts a fresh OpenHands conversation that resumes from
docs/STATUS.md.

It fails open. Any error leaves the loop alone and exits 0, because a watchdog
that stops the loop is worse than one that misses a restart.

Guardrails (all enforced here, not in the conversation):
  * one active run at a time,
  * at most WATCHDOG_MAX_RESTARTS_24H restarts per 24h,
  * a kill switch file (default docs/WATCHDOG_OFF) that stops it outright,
  * every restart appended to docs/STATUS.md.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

GITHUB_API = "https://api.github.com"
OH_BASE = os.environ.get("OPENHANDS_BASE_URL", "https://app.all-hands.dev").rstrip("/")
TITLE_PREFIX = "watchdog:"

# A conversation in one of these states is alive; do not start a second one.
ACTIVE_STATUSES = frozenset({"running", "waiting"})


@dataclass(frozen=True)
class Decision:
    restart: bool
    reason: str


def parse_blocker(status_text: str) -> str:
    """Return the BLOCKER value from docs/STATUS.md, or "" when absent."""
    for line in status_text.splitlines():
        m = re.match(r"^\**BLOCKER\**:\s*(.*)$", line.strip(), re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def status_next(status_text: str) -> str:
    """Return the value of the `Next:` line from docs/STATUS.md, or ""."""
    for line in status_text.splitlines():
        m = re.match(r"^\**Next\**:\s*(.*)$", line.strip(), re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def ready_items(backlog_text: str) -> list[str]:
    """Unchecked backlog lines marked status=ready."""
    out = []
    for line in backlog_text.splitlines():
        if re.match(r"^\s*-\s*\[ \]", line) and "status=ready" in line:
            out.append(line.strip())
    return out


def unfinished_work(status_text: str, backlog_text: str) -> tuple[bool, str]:
    """Is there work the loop has not finished?

    A declared BLOCKER means the loop is deliberately paused, so that is *not*
    unfinished work: restarting would fight the pause.
    """
    blocker = parse_blocker(status_text)
    if blocker and blocker.lower() != "none":
        return False, f"paused by BLOCKER: {blocker}"

    ready = ready_items(backlog_text)
    if ready:
        return True, f"{len(ready)} status=ready backlog item(s)"

    nxt = status_next(status_text)
    if nxt and not nxt.lower().startswith("none"):
        return True, f"STATUS.md Next: {nxt[:120]}"

    return False, "no ready backlog item and STATUS.md Next is none"


def parse_iso(value: str) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def latest_activity(*date_groups: list[str]) -> dt.datetime | None:
    """Newest timestamp across the given groups of ISO-8601 strings."""
    best: dt.datetime | None = None
    for group in date_groups:
        for raw in group:
            ts = parse_iso(raw)
            if ts and (best is None or ts > best):
                best = ts
    return best


def is_stale(last_activity: dt.datetime | None, now: dt.datetime, stale_minutes: int) -> tuple[bool, str]:
    if last_activity is None:
        return True, "no activity recorded"
    age = (now - last_activity).total_seconds() / 60.0
    if age >= stale_minutes:
        return True, f"no activity for {age:.0f} min (limit {stale_minutes})"
    return False, f"activity {age:.0f} min ago (limit {stale_minutes})"


def count_active_runs(items: list[dict]) -> int:
    return sum(1 for it in items if str(it.get("execution_status") or "").lower() in ACTIVE_STATUSES)


def count_restarts(items: list[dict], now: dt.datetime, hours: int = 24) -> int:
    cutoff = now - dt.timedelta(hours=hours)
    n = 0
    for it in items:
        if not str(it.get("title") or "").startswith(TITLE_PREFIX):
            continue
        created = parse_iso(it.get("created_at") or "")
        if created and created >= cutoff:
            n += 1
    return n


def decide(
    *,
    unfinished: bool,
    unfinished_reason: str,
    stale: bool,
    stale_reason: str,
    kill_switch: bool,
    active_runs: int,
    restarts_24h: int,
    max_restarts: int,
) -> Decision:
    """The whole guardrail ladder, in order, as a pure function."""
    if kill_switch:
        return Decision(False, "kill switch present")
    if not unfinished:
        return Decision(False, f"no unfinished work ({unfinished_reason})")
    if active_runs > 0:
        return Decision(False, f"{active_runs} run(s) already active")
    if restarts_24h >= max_restarts:
        return Decision(False, f"restart cap reached ({restarts_24h}/{max_restarts} in 24h)")
    if not stale:
        return Decision(False, f"not stalled ({stale_reason})")
    return Decision(True, f"stalled with work left — {unfinished_reason}; {stale_reason}")


def insert_status_line(status_text: str, line: str) -> str:
    """Add `line` as the newest entry under `Last 5 actions:`, else append."""
    lines = status_text.splitlines()
    for i, raw in enumerate(lines):
        if raw.strip().lower().startswith("last 5 actions"):
            merged = lines[: i + 1] + [line] + lines[i + 1 :]
            return "\n".join(merged).rstrip("\n") + "\n"
    return status_text.rstrip("\n") + "\n" + line + "\n"


def restart_prompt(number: int, stamp: str, reason: str) -> str:
    return (
        f"WATCHDOG RESTART #{number} at {stamp} UTC.\n\n"
        "The previous run of this repository's autonomous loop died mid-task. The model proxy "
        "returned an error page, OpenHands set execution_status=error, and nothing restarted it. "
        "You are the replacement run, started from OUTSIDE that conversation by "
        ".github/workflows/watchdog.yml. Reason for this restart: " + reason + "\n\n"
        "Resume the loop from the ledger, not from scratch:\n"
        "1. Read docs/STATUS.md first, then docs/BACKLOG.md, then docs/LOOP.md and the "
        "self-driving-loop skill.\n"
        "2. Take the first `status=ready` backlog item, or the item named in STATUS.md `Next:`. "
        "Do at most ONE item this run.\n"
        "3. Append this line to docs/STATUS.md as the newest `Last 5 actions` entry:\n"
        f"   - watchdog restart #{number} at {stamp} UTC: previous run stalled; resumed from STATUS.md.\n"
        "4. Follow docs/LOOP.md exactly: branch, draft PR, run scripts/validate.py, "
        "scripts/loader_smoke.py and tests/hooks_test.sh, then the pr-auditor sub-agent. Merge only "
        "under the grant in docs/LOOP.md.\n"
        "5. Never push to main. Never merge HIGH-risk PRs.\n"
        "6. If there is nothing to do, write one `idle` line in docs/STATUS.md and finish.\n"
        "Stop conditions are in docs/LOOP.md."
    )


def http_json(url: str, *, method: str = "GET", headers: dict | None = None, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
    return json.loads(raw) if raw else {}


def gh_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def read_local(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def gh_get(path: str, token: str) -> dict | list:
    return http_json(f"{GITHUB_API}{path}", headers=gh_headers(token))


def commit_status_line(repo: str, token: str, line: str, message: str) -> bool:
    """Append `line` to docs/STATUS.md on main. One retry on a lost race."""
    path = "/repos/{repo}/contents/docs/STATUS.md".format(repo=repo)
    for _ in range(2):
        try:
            cur = gh_get(path, token)
            text = ""
            sha = None
            if isinstance(cur, dict) and cur.get("content"):
                import base64

                text = base64.b64decode(cur["content"]).decode()
                sha = cur.get("sha")
            updated = insert_status_line(text, line)
            payload = {
                "message": message,
                "content": __import__("base64").b64encode(updated.encode()).decode(),
            }
            if sha:
                payload["sha"] = sha
            http_json(f"{GITHUB_API}{path}", method="PUT", headers=gh_headers(token), body=payload)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 409:
                continue
            print(f"watchdog: could not log to STATUS.md: HTTP {e.code}", file=sys.stderr)
            return False
        except Exception as e:  # noqa: BLE001 - logging must never stop a restart
            print(f"watchdog: could not log to STATUS.md: {e}", file=sys.stderr)
            return False
    return False


def start_conversation(api_key: str, repo: str, prompt: str, title: str) -> str | None:
    body = {
        "initial_message": {"content": [{"type": "text", "text": prompt}]},
        "selected_repository": repo,
        "title": title,
    }
    try:
        data = http_json(
            f"{OH_BASE}/api/v1/app-conversations",
            method="POST",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"},
            body=body,
        )
    except urllib.error.HTTPError as e:
        print(f"watchdog: could not start conversation: HTTP {e.code} {e.read().decode()[:300]}", file=sys.stderr)
        return None
    return data.get("id")


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    dry_run = os.environ.get("WATCHDOG_DRY_RUN") == "1" or "--dry-run" in argv

    repo = os.environ.get("GITHUB_REPOSITORY", "madnessgate44-debug/Openhands")
    gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    oh_key = os.environ.get("OPENHANDS_API_KEY") or ""
    kill_path = os.environ.get("WATCHDOG_KILL_SWITCH", "docs/WATCHDOG_OFF")
    stale_minutes = int(os.environ.get("WATCHDOG_STALE_MINUTES", "45"))
    max_restarts = int(os.environ.get("WATCHDOG_MAX_RESTARTS_24H", "6"))

    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.strftime("%Y-%m-%d %H:%M")

    status_text = read_local("docs/STATUS.md")
    backlog_text = read_local("docs/BACKLOG.md")
    unfinished, unfinished_reason = unfinished_work(status_text, backlog_text)
    kill_switch = os.path.exists(kill_path)

    if not gh_token or not oh_key:
        missing = [n for n, v in (("GITHUB_TOKEN", gh_token), ("OPENHANDS_API_KEY", oh_key)) if not v]
        print(f"watchdog: missing {' and '.join(missing)}; failing open (no restart).")
        return 0

    commit_dates, pr_dates, comment_dates, convos = [], [], [], []
    activity_error = ""
    try:
        commits = gh_get(f"/repos/{repo}/commits?sha=main&per_page=1", gh_token)
        prs = gh_get(f"/repos/{repo}/pulls?state=all&sort=updated&direction=desc&per_page=1", gh_token)
        comments = gh_get(f"/repos/{repo}/issues/comments?sort=updated&direction=desc&per_page=1", gh_token)
        convos = http_json(
            f"{OH_BASE}/api/v1/app-conversations/search?limit=50",
            headers={"Authorization": f"Bearer {oh_key}", "Accept": "application/json"},
        ).get("items", [])
        if isinstance(commits, list):
            commit_dates = [(c.get("commit", {}).get("committer", {}) or {}).get("date", "") for c in commits]
        if isinstance(prs, list):
            pr_dates = [p.get("updated_at", "") for p in prs]
        if isinstance(comments, list):
            comment_dates = [c.get("updated_at", "") for c in comments]
    except Exception as e:  # noqa: BLE001 - fail open
        activity_error = str(e)

    if activity_error:
        print(f"watchdog: could not read activity ({activity_error}); failing open (no restart).", file=sys.stderr)
        print(f"watchdog: decision=SKIP — could not read activity ({activity_error})")
        return 0

    last = latest_activity(commit_dates, pr_dates, comment_dates)
    stale, stale_reason = is_stale(last, now, stale_minutes)
    active = count_active_runs(convos)
    restarts = count_restarts(convos, now)

    d = decide(
        unfinished=unfinished,
        unfinished_reason=unfinished_reason,
        stale=stale,
        stale_reason=stale_reason,
        kill_switch=kill_switch,
        active_runs=active,
        restarts_24h=restarts,
        max_restarts=max_restarts,
    )

    print(f"watchdog: unfinished={unfinished} ({unfinished_reason})")
    print(f"watchdog: stale={stale} ({stale_reason})")
    print(f"watchdog: active_runs={active} restarts_24h={restarts}/{max_restarts} kill_switch={kill_switch}")
    print(f"watchdog: decision={'RESTART' if d.restart else 'SKIP'} — {d.reason}")

    if not d.restart:
        return 0
    if dry_run:
        print("watchdog: dry run, not starting a conversation")
        return 0

    number = restarts + 1
    title = f"{TITLE_PREFIX} restart #{number} — {stamp} UTC"
    convo_id = start_conversation(oh_key, repo, restart_prompt(number, stamp, d.reason), title)
    if not convo_id:
        return 0
    print(f"watchdog: started conversation {convo_id}")

    line = f"- watchdog restart #{number} at {stamp} UTC: {d.reason} (conversation {convo_id})."
    commit_status_line(repo, gh_token, line, f"chore(watchdog): log restart #{number}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

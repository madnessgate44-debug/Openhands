#!/bin/bash
# Tests for scripts/watchdog.py: the out-of-conversation loop watchdog.
#
#   tests/watchdog_test.sh
#
# The watchdog's job is to restart a stalled loop, so the cases that matter most
# are the ones where it must NOT restart: a declared blocker, a live run, a
# spent restart budget, a fresh commit, or the kill switch.
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
WD="$ROOT/scripts/watchdog.py"

PASS=0
FAIL=0

# Run a python snippet that imports the watchdog and prints one value.
wd_py() {
  PYTHONPATH="$ROOT/scripts" python3 -c "$1"
}

check() {
  # $1 = label, $2 = actual, $3 = expected
  if [ "$2" = "$3" ]; then
    PASS=$((PASS + 1)); printf 'PASS watchdog %s\n' "$1"
  else
    FAIL=$((FAIL + 1)); printf 'FAIL watchdog %s (got %s, expected %s)\n' "$1" "$2" "$3"
  fi
}

echo "=== watchdog.py: unfinished_work ==="

check "BLOCKER pauses work" \
  "$(wd_py 'import watchdog as w; print(w.unfinished_work("BLOCKER: paused by inbox\nNext: BL-9\n","- [ ] BL-9 | x | y | risk=low | status=ready\n")[0])')" \
  "False"

check "BLOCKER none does not pause" \
  "$(wd_py 'import watchdog as w; print(w.unfinished_work("BLOCKER: none\n","- [ ] BL-9 | x | y | risk=low | status=ready\n")[0])')" \
  "True"

check "ready item counts as work" \
  "$(wd_py 'import watchdog as w; print(w.unfinished_work("BLOCKER: none\n","- [ ] BL-9 | x | y | risk=low | status=ready\n")[1])')" \
  "1 status=ready backlog item(s)"

check "done items are not work" \
  "$(wd_py 'import watchdog as w; print(w.unfinished_work("BLOCKER: none\nNext: none\n","- [x] BL-9 | x | y | risk=low | status=done\n")[0])')" \
  "False"

check "a Next: line is work" \
  "$(wd_py 'import watchdog as w; print(w.unfinished_work("BLOCKER: none\nNext: BL-7 finish the thing\n","")[0])')" \
  "True"

check "Next: none is not work" \
  "$(wd_py 'import watchdog as w; print(w.unfinished_work("BLOCKER: none\nNext: none\n","")[0])')" \
  "False"

check "ready item with no space after dash still counts" \
  "$(wd_py 'import watchdog as w; print(w.unfinished_work("BLOCKER: none\n","- [ ]BL-9 | x | y | status=ready\n")[1])')" \
  "1 status=ready backlog item(s)"

echo "=== watchdog.py: staleness ==="

check "45 min of silence is stale" \
  "$(wd_py 'import datetime as dt, watchdog as w; n=dt.datetime(2026,10,30,12,0,tzinfo=dt.timezone.utc); print(w.is_stale(n-dt.timedelta(minutes=45), n, 45)[0])')" \
  "True"

check "44 min of silence is fresh" \
  "$(wd_py 'import datetime as dt, watchdog as w; n=dt.datetime(2026,10,30,12,0,tzinfo=dt.timezone.utc); print(w.is_stale(n-dt.timedelta(minutes=44), n, 45)[0])')" \
  "False"

check "no activity at all is stale" \
  "$(wd_py 'import datetime as dt, watchdog as w; n=dt.datetime(2026,10,30,12,0,tzinfo=dt.timezone.utc); print(w.is_stale(None, n, 45)[0])')" \
  "True"

echo "=== watchdog.py: restart accounting ==="

check "running and waiting count as active" \
  "$(wd_py 'import watchdog as w; print(w.count_active_runs([{"execution_status":"running"},{"execution_status":"waiting"},{"execution_status":"finished"}]))')" \
  "2"

check "only watchdog titles count toward the cap" \
  "$(wd_py 'import datetime as dt, watchdog as w; n=dt.datetime(2026,10,30,12,0,tzinfo=dt.timezone.utc); items=[{"title":"watchdog: restart #1 — x","created_at":"2026-10-30T11:00:00Z"},{"title":"Openhands loop — y","created_at":"2026-10-30T11:30:00Z"},{"title":"watchdog: restart #2 — x","created_at":"2026-10-29T11:00:00Z"}]; print(w.count_restarts(items,n))')" \
  "1"

echo "=== watchdog.py: decide() guardrail ladder ==="

check "kill switch wins over everything" \
  "$(wd_py 'import watchdog as w; print(w.decide(unfinished=True,unfinished_reason="r",stale=True,stale_reason="s",kill_switch=True,active_runs=0,restarts_24h=0,max_restarts=6).restart)')" \
  "False"

check "an active run blocks a second" \
  "$(wd_py 'import watchdog as w; print(w.decide(unfinished=True,unfinished_reason="r",stale=True,stale_reason="s",kill_switch=False,active_runs=1,restarts_24h=0,max_restarts=6).restart)')" \
  "False"

check "the 24h cap blocks the 7th restart" \
  "$(wd_py 'import watchdog as w; print(w.decide(unfinished=True,unfinished_reason="r",stale=True,stale_reason="s",kill_switch=False,active_runs=0,restarts_24h=6,max_restarts=6).restart)')" \
  "False"

check "fresh activity blocks a restart" \
  "$(wd_py 'import watchdog as w; print(w.decide(unfinished=True,unfinished_reason="r",stale=False,stale_reason="s",kill_switch=False,active_runs=0,restarts_24h=0,max_restarts=6).restart)')" \
  "False"

check "no work blocks a restart" \
  "$(wd_py 'import watchdog as w; print(w.decide(unfinished=False,unfinished_reason="r",stale=True,stale_reason="s",kill_switch=False,active_runs=0,restarts_24h=0,max_restarts=6).restart)')" \
  "False"

check "stalled with work left restarts" \
  "$(wd_py 'import watchdog as w; print(w.decide(unfinished=True,unfinished_reason="r",stale=True,stale_reason="s",kill_switch=False,active_runs=0,restarts_24h=0,max_restarts=6).restart)')" \
  "True"

echo "=== watchdog.py: STATUS.md logging ==="

check "restart line lands under Last 5 actions" \
  "$(wd_py 'import watchdog as w; print(w.insert_status_line("BLOCKER: none\nLast 5 actions:\n- old one\nNext: none\n","- watchdog restart #1 at x UTC: y.").splitlines()[2])')" \
  "- watchdog restart #1 at x UTC: y."

check "logging with no Last 5 actions still appends" \
  "$(wd_py 'import watchdog as w; print(w.insert_status_line("BLOCKER: none\n","- watchdog restart #1 at x UTC: y.").splitlines()[-1])')" \
  "- watchdog restart #1 at x UTC: y."

check "restart prompt names the watchdog" \
  "$(wd_py 'import watchdog as w; print("WATCHDOG RESTART" in w.restart_prompt(1,"2026-10-31 04:00","stalled"))')" \
  "True"

check "restart prompt forbids pushing to main" \
  "$(wd_py 'import watchdog as w; print("Never push to main" in w.restart_prompt(1,"2026-10-31 04:00","stalled"))')" \
  "True"

echo "=== watchdog.py: fails open without credentials ==="

NOENV_OUT="$(cd "$ROOT" && env -u GITHUB_TOKEN -u GH_TOKEN -u OPENHANDS_API_KEY GITHUB_REPOSITORY=owner/repo python3 scripts/watchdog.py 2>&1; echo "rc=$?")"
if printf '%s' "$NOENV_OUT" | grep -q 'rc=0'; then
  PASS=$((PASS + 1)); printf 'PASS watchdog missing credentials exits 0\n'
else
  FAIL=$((FAIL + 1)); printf 'FAIL watchdog missing credentials (%s)\n' "$NOENV_OUT"
fi

DRY_OUT="$(cd "$ROOT" && WATCHDOG_DRY_RUN=1 GITHUB_TOKEN=x OPENHANDS_API_KEY=y python3 scripts/watchdog.py 2>&1; echo "rc=$?")"
if printf '%s' "$DRY_OUT" | grep -q 'decision='; then
  PASS=$((PASS + 1)); printf 'PASS watchdog dry run reports a decision\n'
else
  FAIL=$((FAIL + 1)); printf 'FAIL watchdog dry run (%s)\n' "$DRY_OUT"
fi

echo
echo "-----------------------------------"
printf 'TOTAL: %s passed, %s failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]

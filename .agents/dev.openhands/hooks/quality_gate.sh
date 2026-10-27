#!/bin/bash
# Stop hook: refuse to let the agent finish while a real gate fails.
#
# Design notes:
#  * Only enforce gates that exist in this project, so it never blocks on
#    missing tooling.
#  * `git diff --check` sees only the working tree, so it passes vacuously once
#    the changes are committed. We therefore also check committed changes
#    against the merge-base with origin/main (falling back to HEAD~1).
#  * A loop breaker caps consecutive denials: after MAX_DENIALS the gate allows
#    the stop and prints a loud warning, so a stuck agent cannot be trapped
#    forever by a gate it cannot satisfy.
set -u

cd "${OPENHANDS_PROJECT_DIR:-.}" 2>/dev/null || exit 0

MAX_DENIALS=3
project_key="$(printf '%s' "$(pwd)" | cksum | cut -d' ' -f1)"
state_file="/tmp/openhands_quality_gate_${project_key}"

deny() {
  count=0
  [ -f "$state_file" ] && count="$(cat "$state_file" 2>/dev/null || echo 0)"
  case "$count" in ''|*[!0-9]*) count=0 ;; esac
  count=$((count + 1))
  printf '%s' "$count" >"$state_file"
  if [ "$count" -gt "$MAX_DENIALS" ]; then
    msg="Quality gate BYPASSED after ${count} consecutive denials (limit ${MAX_DENIALS}). Reason: $1"
    printf '{"decision":"allow","reason":"%s"}\n' "$msg"
    exit 0
  fi
  printf '{"decision":"deny","reason":"%s"}\n' "$1"
  exit 2
}

clear_state() { rm -f "$state_file" 2>/dev/null || true; }

# 1. Whitespace errors in the working tree.
if [ -d .git ]; then
  bad="$(git diff --check 2>/dev/null)"
  if [ -n "$bad" ]; then
    deny "git diff --check reports whitespace errors in the working tree (often a trailing blank line at EOF). Fix them before finishing: perl -0pi -e 's/\\n+\\z/\\n/' <files>"
  fi

  # 2. Whitespace errors in committed changes, which `git diff --check` misses.
  if git rev-parse --verify -q origin/main >/dev/null 2>&1; then
    base="$(git merge-base origin/main HEAD 2>/dev/null)"
  else
    base="$(git rev-parse --verify -q HEAD~1 2>/dev/null)"
  fi
  if [ -n "${base:-}" ]; then
    bad_committed="$(git diff --check "$base" HEAD 2>/dev/null)"
    if [ -n "$bad_committed" ]; then
      deny "git diff --check reports whitespace errors in committed changes (base ${base}). Fix them before finishing."
    fi
  fi
fi

# 3. Typecheck gate, only if a script exists.
if [ -f package.json ] && grep -q '"typecheck"' package.json 2>/dev/null; then
  if ! npm run --silent typecheck >/tmp/tsc_gate.log 2>&1; then
    deny "Typecheck failed. Fix the errors before finishing (see /tmp/tsc_gate.log)."
  fi
fi

# All gates passed: reset the denial counter.
clear_state
exit 0

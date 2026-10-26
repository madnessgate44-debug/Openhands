#!/bin/bash
# Stop hook: refuse to let the agent finish while the real gate fails.
# Only enforces gates that exist in this project, so it never blocks on missing tooling.
set -u

cd "${OPENHANDS_PROJECT_DIR:-.}" 2>/dev/null || exit 0

deny() {
  printf '{"decision":"deny","reason":"%s"}\n' "$1"
  exit 2
}

# Trailing-blank-line trap: run_check runs `git diff --check`, which fails on a blank line at EOF.
if [ -d .git ]; then
  bad="$(git diff --check 2>/dev/null)"
  if [ -n "$bad" ]; then
    deny "git diff --check reports whitespace errors (often a trailing blank line at EOF). Fix them before finishing: perl -0pi -e 's/\\n+\\z/\\n/' <files>"
  fi
fi

# Typecheck gate, only if a script exists.
if [ -f package.json ] && grep -q '"typecheck"' package.json 2>/dev/null; then
  if ! npm run --silent typecheck >/tmp/tsc_gate.log 2>&1; then
    deny "Typecheck failed. Fix the errors before finishing (see /tmp/tsc_gate.log)."
  fi
fi

exit 0

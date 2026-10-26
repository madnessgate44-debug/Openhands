#!/bin/bash
# PreToolUse guard: deny destructive or secret-leaking terminal commands.
# Reads the hook JSON payload on stdin.
set -u

payload="$(cat)"
cmd="$(printf '%s' "$payload" | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin)
    print(d.get("tool_input",{}).get("command",""))
except Exception:
    print("")' 2>/dev/null)"

deny() {
  printf '{"decision":"deny","reason":"%s"}\n' "$1"
  exit 2
}

case "$cmd" in
  *"rm -rf /"*|*"rm -rf /*"*) deny "Refusing to run a recursive delete of the filesystem root." ;;
  *"git push"*"--force"*"main"*|*"git push"*"main"*"--force"*) deny "Refusing to force-push to main." ;;
  *"git push"*"--no-verify"*) deny "Refusing to bypass push hooks with --no-verify." ;;
  *"git push"*"origin"*"main"*|*"git push"*" main"*) deny "Refusing to push directly to main; use a branch." ;;
esac

# Block commands that would print a raw secret value.
case "$cmd" in
  *"echo \$GITHUB_TOKEN"*|*"echo \$OPENHANDS_API_KEY"*|*"echo \$VERCEL_TOKEN"*|*"env |"*|*"printenv"*)
    deny "Refusing to print environment secrets to the transcript." ;;
esac

exit 0

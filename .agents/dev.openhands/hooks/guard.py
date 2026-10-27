#!/usr/bin/env python3
"""PreToolUse guard decision logic.

Reads the hook event JSON on stdin and denies destructive or secret-leaking
terminal commands. Exit 2 with {"decision":"deny","reason":...} to block, exit 0
to allow.

Matching runs on a normalized command: the payload is parsed as JSON, the shell
command is split into tokens with quote/escape handling, and patterns are
evaluated against those tokens rather than raw substrings. This avoids the two
failure modes of substring matching -- bypasses (extra spaces, quoting, flags
split across argv) and false positives (a branch name that merely contains
"main").
"""
from __future__ import annotations

import json
import re
import shlex
import sys


def read_command() -> str:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return ""
    if not isinstance(payload, dict):
        return ""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    command = tool_input.get("command")
    return command if isinstance(command, str) else ""


def tokens(command: str) -> list[str]:
    """Split a shell command into tokens, keeping shell operators separate.

    ``shlex.split`` leaves a ``;`` attached to the preceding word (``hi;``), so
    operators would not be seen as segment boundaries. ``shlex.shlex`` with
    ``punctuation_chars`` makes ``; | & ( ) < >`` standalone tokens, which lets
    :func:`segments` split reliably.
    """
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return command.split()


def segments(argv: list[str]) -> list[list[str]]:
    """Split argv into simple commands on shell operators."""
    out: list[list[str]] = []
    current: list[str] = []
    separators = {"|", "||", "&&", ";", "&", "(", ")", ";;", "|&"}
    for tok in argv:
        if tok in separators:
            if current:
                out.append(current)
            current = []
        else:
            current.append(tok)
    if current:
        out.append(current)
    return out


def deny(reason: str) -> None:
    print(json.dumps({"decision": "deny", "reason": reason}))
    sys.exit(2)


FORCE_FLAGS = {"-f", "--force", "--force-with-lease", "--force-if-includes"}
PROTECTED = {"main", "master"}


def is_refspec_to_protected(tok: str) -> bool:
    """True for `src:dst` or `+src:dst` refspecs whose destination is main/master."""
    body = tok[1:] if tok.startswith("+") else tok
    if ":" not in body:
        return False
    dst = body.split(":", 1)[1]
    short = dst.rsplit("/", 1)[-1]
    return short in PROTECTED


def check_git_push(argv: list[str]) -> None:
    if len(argv) < 2 or argv[0] != "git" or argv[1] != "push":
        return
    rest = argv[2:]
    if any(t == "--no-verify" or t.startswith("--no-verify") for t in rest):
        deny("Refusing to bypass git hooks with --no-verify.")
    force = any(t in FORCE_FLAGS for t in rest) or any(
        t.startswith("--force-with-lease") for t in rest
    )
    positionals = [t for t in rest if not t.startswith("-")]
    ref_args = positionals[1:] if positionals else []
    targets_protected = False
    for tok in ref_args:
        if is_refspec_to_protected(tok):
            targets_protected = True
            break
        if tok.rsplit("/", 1)[-1] in PROTECTED:
            targets_protected = True
            break
    if force:
        deny("Refusing to force-push (--force/-f/--force-with-lease). Push to a branch instead.")
    if targets_protected:
        deny(
            "Refusing to push to main/master (including HEAD:main and refspecs). "
            "Push to a branch and open a pull request."
        )


RM_TARGETS = {"/", "/*", "~", "~/", "$HOME", "${HOME}", "~/*"}


def check_rm(argv: list[str]) -> None:
    if not argv or argv[0] != "rm":
        return
    recursive = False
    targets: list[str] = []
    for tok in argv[1:]:
        if tok == "--recursive":
            recursive = True
        elif tok.startswith("--"):
            continue
        elif tok.startswith("-") and len(tok) > 1:
            if "r" in tok[1:] or "R" in tok[1:]:
                recursive = True
        else:
            targets.append(tok)
    if not recursive:
        return
    for t in targets:
        if t in RM_TARGETS or t.rstrip("/") in {"", "~"}:
            deny(f"Refusing a recursive delete of a filesystem-root or home path: {t}")


SECRET_VARS = re.compile(
    r"\$(?:\{)?(GITHUB_TOKEN|OPENHANDS_API_KEY|VERCEL_TOKEN|AWS_SECRET_ACCESS_KEY|GH_TOKEN)(?:\})?"
)
SECRET_READERS = {
    "echo", "printf", "printenv", "env", "set", "export",
    "cat", "bat", "less", "more", "head", "tail",
}


def check_secret_print(argv: list[str]) -> None:
    if not argv:
        return
    prog = argv[0].rsplit("/", 1)[-1]
    joined = " ".join(argv)
    if SECRET_VARS.search(joined):
        deny("Refusing to print an environment secret value to the transcript.")
    if prog in ("printenv", "env") and len(argv) == 1:
        deny(f"Refusing to dump all environment secrets with {prog}.")
    if prog in SECRET_READERS:
        for tok in argv[1:]:
            base = tok.rsplit("/", 1)[-1]
            if "environ" in tok and tok.startswith("/proc/"):
                deny("Refusing to read /proc/*/environ (process secrets).")
            if re.fullmatch(r"\.env(\.[\w.-]+)?", base):
                deny(f"Refusing to read a .env file ({tok}) into the transcript.")


PIPE_SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish"}


def check_pipe_to_shell(argv: list[str]) -> None:
    """Deny `curl ... | sh` / `wget ... | bash` style remote-code execution."""
    segs = segments(argv)
    for i, seg in enumerate(segs[:-1]):
        if not seg:
            continue
        prog = seg[0].rsplit("/", 1)[-1]
        if prog not in {"curl", "wget"}:
            continue
        nxt = segs[i + 1]
        if nxt and nxt[0].rsplit("/", 1)[-1] in PIPE_SHELLS:
            deny(f"Refusing to pipe {prog} output directly into a shell.")


def main() -> int:
    command = read_command()
    if not command.strip():
        return 0
    argv = tokens(command)
    for seg in segments(argv):
        if not seg:
            continue
        check_git_push(seg)
        check_rm(seg)
        check_secret_print(seg)
    check_pipe_to_shell(argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())

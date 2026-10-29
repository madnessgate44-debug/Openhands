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

The guard stops honest mistakes. It is not a security boundary: a determined
command can get around it. See the README Hooks section.
"""
from __future__ import annotations

import json
import re
import shlex
import sys

MAX_DEPTH = 3


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


def prog_of(tok: str) -> str:
    return tok.rsplit("/", 1)[-1]


# --------------------------------------------------------------------------- #
# git
# --------------------------------------------------------------------------- #

# git global options that take a separate value, and flag-only options, skipped
# before the subcommand is read.
GIT_VALUE_OPTS = {
    "-C", "-c", "--git-dir", "--work-tree", "--namespace",
    "--exec-path", "--config-env", "--super-prefix",
}
GIT_FLAG_OPTS = {
    "--no-pager", "--no-replace-objects", "-p", "--paginate", "--bare",
    "--literal-pathspecs", "--glob-pathspecs", "--noglob-pathspecs",
    "--icase-pathspecs", "--version", "--help", "-P", "--no-optional-locks",
    "--no-advice", "--no-lazy-fetch",
}
FORCE_FLAGS = {"-f", "--force", "--force-with-lease", "--force-if-includes"}
PROTECTED = {"main", "master"}
SHORT_FORCE = "f"


def git_subcommand(argv: list[str]) -> tuple[str | None, int]:
    """Return (subcommand, index) skipping git's global options."""
    if not argv or prog_of(argv[0]) != "git":
        return None, -1
    i = 1
    while i < len(argv):
        t = argv[i]
        if t in GIT_VALUE_OPTS:
            i += 2
            continue
        if t.startswith("--") and any(t.startswith(o + "=") for o in GIT_VALUE_OPTS):
            i += 1
            continue
        if t in GIT_FLAG_OPTS:
            i += 1
            continue
        if t.startswith("-"):
            # `-C<path>` / `-c<kv>` written without a space, or any other flag.
            i += 1
            continue
        return t, i
    return None, -1


def is_refspec_to_protected(tok: str) -> bool:
    """True for `src:dst` or `+src:dst` refspecs whose destination is main/master."""
    body = tok[1:] if tok.startswith("+") else tok
    if ":" not in body:
        return False
    dst = body.split(":", 1)[1]
    return dst.rsplit("/", 1)[-1] in PROTECTED


def push_is_force(rest: list[str]) -> bool:
    for t in rest:
        if t in FORCE_FLAGS or t.startswith("--force-with-lease") or t.startswith("--force-if-includes"):
            return True
        if t.startswith("+"):
            return True
        if t.startswith("-") and not t.startswith("--") and len(t) > 1:
            if SHORT_FORCE in t[1:]:
                return True
    return False


def short_group_has(tok: str, letter: str) -> bool:
    return tok.startswith("-") and not tok.startswith("--") and letter in tok[1:]


def check_git(argv: list[str]) -> None:
    sub, idx = git_subcommand(argv)
    if sub is None:
        return
    rest = argv[idx + 1:]

    if any(t == "--no-verify" or t.startswith("--no-verify") for t in rest):
        deny("Refusing to bypass git hooks with --no-verify.")

    if sub == "commit" and any(short_group_has(t, "n") for t in rest):
        deny("Refusing to bypass git hooks with `git commit -n` (--no-verify).")

    if sub != "push":
        return

    for flag in ("--all", "--mirror"):
        if flag in rest:
            deny(
                f"Refusing `git push {flag}`; it can include main/master. "
                "Push one branch and open a pull request."
            )
    if push_is_force(rest):
        deny("Refusing to force-push (--force/-f/-fu/--force-with-lease/+ref). Push to a branch instead.")

    positionals = [t for t in rest if not t.startswith("-")]
    ref_args = positionals[1:] if positionals else []
    for tok in ref_args:
        if is_refspec_to_protected(tok) or tok.rsplit("/", 1)[-1] in PROTECTED:
            deny(
                "Refusing to push to main/master (including HEAD:main and refspecs). "
                "Push to a branch and open a pull request."
            )


# --------------------------------------------------------------------------- #
# rm -rf
# --------------------------------------------------------------------------- #

SYSTEM_DIRS = {
    "/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/opt", "/proc",
    "/root", "/sbin", "/sys", "/usr", "/var", "/lib64", "/srv", "/run",
}
RM_DENY = {"/", "/*", "~", "~/", "~/*", "$HOME", "${HOME}", ".git", ".", ".."} | SYSTEM_DIRS


def norm_target(t: str) -> str:
    t = t.strip().strip('"').strip("'")
    while len(t) > 1 and t.endswith("/"):
        t = t[:-1]
    return t


def check_rm(argv: list[str]) -> None:
    if not argv or prog_of(argv[0]) != "rm":
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
        if norm_target(t) in RM_DENY:
            deny(f"Refusing a recursive delete of a filesystem-root, home or system path: {t}")


# --------------------------------------------------------------------------- #
# secrets
# --------------------------------------------------------------------------- #

SECRET_NAME = re.compile(r"(?i)(TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY|PRIVATE_?KEY|CREDENTIAL)")
VAR_RE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")
NAME_ONLY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Commands that write their arguments to stdout. A secret var passed to one of
# these lands in the transcript; a secret var used for auth (a URL or header) does not.
PRINTERS = {
    "echo", "printf", "set", "export",
    "cat", "bat", "less", "more", "head", "tail", "tee",
}


def token_has_secret_var(tok: str) -> bool:
    return any(SECRET_NAME.search(m.group(1)) for m in VAR_RE.finditer(tok))


def check_secret_print(argv: list[str]) -> None:
    if not argv:
        return
    prog = prog_of(argv[0])
    if prog == "printenv":
        args = [a for a in argv[1:] if not a.startswith("-")]
        if not args:
            deny("Refusing to dump all environment secrets with printenv.")
        for a in args:
            if SECRET_NAME.search(a):
                deny(f"Refusing to print the secret environment variable {a} to the transcript.")
        return
    if prog == "env":
        if len(argv) == 1:
            deny("Refusing to dump all environment secrets with env.")
        for a in argv[1:]:
            if a.startswith("-") or "=" in a:
                continue
            if NAME_ONLY.match(a) and SECRET_NAME.search(a):
                deny(f"Refusing to print the secret environment variable {a} to the transcript.")
        return
    if prog not in PRINTERS:
        return
    for tok in argv[1:]:
        if token_has_secret_var(tok):
            deny("Refusing to print an environment secret value to the transcript.")
        base = prog_of(tok)
        if tok.startswith("/proc/") and "environ" in tok:
            deny("Refusing to read /proc/*/environ (process secrets).")
        if re.fullmatch(r"\.env(\.[\w.-]+)?", base):
            deny(f"Refusing to read a .env file ({tok}) into the transcript.")


# --------------------------------------------------------------------------- #
# pipes and wrappers
# --------------------------------------------------------------------------- #

INTERPRETERS = {"sh", "bash", "zsh", "dash", "ksh", "fish", "python", "python3", "node", "perl", "ruby"}
WRAP_SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish"}
WRAP_PREFIX = {"sudo", "command", "nohup", "time", "env", "setsid", "stdbuf", "nice", "ionice"}
VALUE_OPTS = {
    "sudo": {"-u", "-g", "-p", "-C", "-h", "-r", "-t", "-U", "--user", "--group", "--prompt"},
    "timeout": {"-s", "-k", "--signal", "--kill-after"},
    "xargs": {"-I", "-n", "-P", "-L", "-s", "-a", "-d", "-E", "--max-args", "--max-procs"},
}


def check_pipe(argv: list[str]) -> None:
    segs = segments(argv)
    for i, seg in enumerate(segs[:-1]):
        if not seg or prog_of(seg[0]) not in {"curl", "wget"}:
            continue
        nxt = segs[i + 1]
        j = 0
        while j < len(nxt) and prog_of(nxt[j]) in WRAP_PREFIX:
            j += 1
        if j < len(nxt) and prog_of(nxt[j]) in INTERPRETERS:
            deny(f"Refusing to pipe {prog_of(seg[0])} output directly into {prog_of(nxt[j])}.")


def unwrap(seg: list[str]) -> list[str]:
    """Inner command strings hidden behind a wrapper in this segment."""
    if not seg:
        return []
    prog = prog_of(seg[0])
    args = seg[1:]
    if prog in WRAP_SHELLS:
        if "-c" in args:
            k = args.index("-c")
            if k + 1 < len(args) and args[k + 1]:
                return [args[k + 1]]
        return []
    if prog in ("sudo", "timeout", "xargs"):
        opts = VALUE_OPTS[prog]
        i = 0
        while i < len(args) and args[i].startswith("-"):
            i += 2 if args[i] in opts and i + 1 < len(args) else 1
        if prog == "timeout" and i < len(args):
            i += 1  # skip the duration
        return [" ".join(args[i:])] if args[i:] else []
    if prog == "command":
        i = 0
        while i < len(args) and args[i].startswith("-"):
            i += 1
        return [" ".join(args[i:])] if args[i:] else []
    if prog in ("nohup", "time", "setsid", "stdbuf", "nice", "ionice"):
        i = 0
        while i < len(args) and args[i].startswith("-"):
            i += 1
        return [" ".join(args[i:])] if args[i:] else []
    if prog == "env":
        i = 0
        while i < len(args):
            a = args[i]
            if a.startswith("-"):
                i += 1
                continue
            if re.match(r"[A-Za-z_][A-Za-z0-9_]*=", a):
                i += 1
                continue
            break
        return [" ".join(args[i:])] if args[i:] else []
    if prog == "eval":
        return [" ".join(args)] if args else []
    return []


# --------------------------------------------------------------------------- #
# heredocs
# --------------------------------------------------------------------------- #

SHELL_BODY_CONSUMERS = {"sh", "bash", "zsh", "dash", "ksh", "fish", "source", "eval"}


def heredoc_ops(line: str) -> list[tuple[int, int, bool, str]]:
    """Return (start, end, strip_tabs, delimiter) for each ``<<`` / ``<<-`` on a line.

    ``<<<`` is a herestring (a one-line argument), not a heredoc, and is skipped,
    as is a ``<<`` that is itself preceded by ``<``. A quoted or backslash-escaped
    delimiter is unwrapped to the bare word that terminates the body.
    """
    ops: list[tuple[int, int, bool, str]] = []
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if c in ("'", '"'):
            i += 1
            while i < n and line[i] != c:
                i += 1
            i += 1
            continue
        if (
            line.startswith("<<", i)
            and not line.startswith("<<<", i)
            and (i == 0 or line[i - 1] != "<")
        ):
            j = i + 2
            strip_tabs = j < n and line[j] == "-"
            if strip_tabs:
                j += 1
            while j < n and line[j] in " \t":
                j += 1
            if j >= n:
                break
            if line[j] in ("'", '"'):
                q = line[j]
                k = j + 1
                while k < n and line[k] != q:
                    k += 1
                delim = line[j + 1:k]
                end = k + 1 if k < n else k
            elif line[j] == "\\":
                delim = line[j + 1] if j + 1 < n else ""
                end = j + 2
            else:
                k = j
                while k < n and (line[k].isalnum() or line[k] == "_"):
                    k += 1
                delim = line[j:k]
                end = k
            if delim:
                ops.append((i, end, strip_tabs, delim))
            i = max(end, i + 1)
            continue
        i += 1
    return ops


def consumer_is_shell(line: str, ops: list[tuple[int, int, bool, str]]) -> bool:
    """True when a shell runs the heredoc body, so the body is code, not data."""
    prefix = line[: ops[0][0]] if ops else line
    return any(prog_of(tok) in SHELL_BODY_CONSUMERS for tok in tokens(prefix))


def fold_continuations(lines: list[str], i: int) -> tuple[str, int]:
    """Join physical lines ending in an odd backslash into one logical line.

    A ``\\`` at end of line is a line continuation, not a command separator, so
    the lines must not be split apart by the newline handling below.
    """
    current = lines[i]
    while current.endswith("\\") and (len(current) - len(current.rstrip("\\"))) % 2 == 1:
        current = current[:-1]
        i += 1
        if i >= len(lines):
            break
        current = current + " " + lines[i].lstrip()
    return current, i


def strip_heredocs(command: str) -> str:
    """Drop heredoc bodies that are data and keep the ones a shell will execute.

    A body is text when the consuming command is not a shell (``cat``, ``tee``,
    ``python``...): its lines are removed so they are not scanned as arguments.
    When the consumer is a shell or ``source``/``eval`` the body is code and its
    lines are kept, so the normal checks still see them. An unterminated heredoc
    fails open: the remaining lines are treated as body text. Newlines become
    ``;`` so a command written after the terminator is checked as its own segment.
    """
    lines = command.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line, i = fold_continuations(lines, i)
        ops = heredoc_ops(line)
        if not ops:
            out.append(line)
            i += 1
            continue
        keep = consumer_is_shell(line, ops)
        out.append(line)
        i += 1
        for _start, _end, strip_tabs, delim in ops:
            body: list[str] = []
            while i < len(lines):
                candidate = lines[i].lstrip("\t") if strip_tabs else lines[i]
                if candidate == delim:
                    i += 1
                    break
                body.append(lines[i])
                i += 1
            if keep:
                out.extend(body)
    return " ; ".join(out)


PROC_SUB = re.compile(
    r"(?<![\w])(bash|sh|zsh|dash|ksh|fish|source|python3?|node|perl|ruby)\s+<\(\s*(curl|wget)\b"
)
SUBST_DOLLAR = re.compile(r"\$\(([^()]*)\)")
SUBST_TICK = re.compile(r"`([^`]*)`")


def check_all(command: str, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        return
    command = strip_heredocs(command).strip()
    if not command:
        return
    argv = tokens(command)
    for seg in segments(argv):
        if not seg:
            continue
        check_git(seg)
        check_rm(seg)
        check_secret_print(seg)
        for inner in unwrap(seg):
            check_all(inner, depth + 1)
    check_pipe(argv)
    for m in SUBST_DOLLAR.finditer(command):
        check_all(m.group(1), depth + 1)
    for m in SUBST_TICK.finditer(command):
        check_all(m.group(1), depth + 1)
    if PROC_SUB.search(command):
        deny("Refusing to run a downloaded script via process substitution (<(...)).")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(
            "account-library guard: could not read the hook payload as JSON; allowing.",
            file=sys.stderr,
        )
        return 0
    if not isinstance(payload, dict):
        print(
            "account-library guard: hook payload is not an object; allowing.",
            file=sys.stderr,
        )
        return 0
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str) or not command.strip():
        return 0
    check_all(command)
    return 0


if __name__ == "__main__":
    sys.exit(main())

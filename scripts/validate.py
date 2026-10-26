#!/usr/bin/env python3
"""Validate the account-library plugin: manifests, frontmatter, skills, agents and hooks.

Exits non-zero with a report on the first structural problem, so CI and a local
pre-commit check can both rely on it.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / ".agents"
FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def check_json(path: Path, required: list[str]) -> dict:
    if not path.exists():
        fail(f"missing {path.relative_to(ROOT)}")
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        fail(f"{path.relative_to(ROOT)}: invalid JSON ({e})")
        return {}
    for key in required:
        if key not in data:
            fail(f"{path.relative_to(ROOT)}: missing required key '{key}'")
    return data


def parse_frontmatter(path: Path) -> dict | None:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        fail(f"{path.relative_to(ROOT)}: no YAML frontmatter")
        return None
    fm: dict = {}
    mode: str | None = None  # "list" or "block"
    key: str | None = None
    for line in m.group(1).splitlines():
        if line.startswith(("  - ", "- ")):
            if key and mode == "list":
                fm.setdefault(key, []).append(
                    line.split("- ", 1)[1].strip().strip("'\"")
                )
            continue
        if mode == "block" and (line.startswith(("  ", "\t")) or not line.strip()):
            if line.strip():
                fm[key] = (fm.get(key, "") + " " + line.strip()).strip()
            continue
        k, _, value = line.partition(":")
        k, value = k.strip(), value.strip()
        if value in (">", "|"):
            key, mode, fm[k] = k, "block", ""
        elif value == "":
            key, mode, fm[k] = k, "list", fm.get(k, [])
        else:
            key, mode, fm[k] = None, None, value.strip("'\"")
    return fm


def main() -> int:
    marketplace = check_json(
        AGENTS / ".plugin" / "marketplace.json", ["name", "owner", "plugins"]
    )
    plugin = check_json(AGENTS / "plugin.json", ["$schema", "name", "version"])
    if plugin and not str(plugin.get("$schema", "")).startswith(
        "https://agent-plugins.org/schemas/"
    ):
        fail("plugin.json: $schema must be the agent-plugins.org 1.0.0 identifier")

    # The marketplace must declare a plugin, or agents/hooks never load.
    if marketplace and not marketplace.get("plugins"):
        fail(
            ".plugin/marketplace.json: declares no plugin, so sub-agents and hooks "
            "will NOT load (a marketplace alone loads only skills)"
        )

    skills_dir = AGENTS / "skills"
    skill_names: set[str] = set()
    for entry in sorted(skills_dir.iterdir()):
        path = entry / "SKILL.md" if entry.is_dir() else entry
        if not path.exists() or path.suffix != ".md":
            continue
        expected = entry.name if entry.is_dir() else entry.stem
        fm = parse_frontmatter(path)
        if fm is None:
            continue
        name = fm.get("name")
        if name != expected:
            fail(f"{path.relative_to(ROOT)}: name '{name}' != '{expected}'")
        if not fm.get("description"):
            fail(f"{path.relative_to(ROOT)}: missing description")
        if "triggers" not in fm and "paths" not in fm:
            fail(f"{path.relative_to(ROOT)}: needs triggers: or paths:")
        skill_names.add(expected)

    agents_dir = AGENTS / "dev.openhands" / "agents"
    agent_names: set[str] = set()
    valid_tools = {"terminal", "file_editor", "task_tracker", "browser_tool_set"}
    for path in sorted(agents_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        fm = parse_frontmatter(path)
        if fm is None:
            continue
        name = fm.get("name")
        if name != path.stem:
            fail(f"{path.relative_to(ROOT)}: name '{name}' != '{path.stem}'")
        if not fm.get("description"):
            fail(f"{path.relative_to(ROOT)}: missing description")
        tools = fm.get("tools") or []
        unknown = [t for t in tools if t not in valid_tools]
        if unknown:
            fail(
                f"{path.relative_to(ROOT)}: unknown tool(s) {unknown}; "
                f"valid names are {sorted(valid_tools)}"
            )
        if fm.get("skills"):
            fail(
                f"{path.relative_to(ROOT)}: sub-agent 'skills:' resolve against the "
                "workspace, not this plugin; remove them to avoid a load failure"
            )
        agent_names.add(name)

    hooks_path = AGENTS / "dev.openhands" / "hooks" / "hooks.json"
    hooks = check_json(hooks_path, [])
    if hooks:
        known = {
            "pre_tool_use",
            "post_tool_use",
            "user_prompt_submit",
            "session_start",
            "session_end",
            "stop",
        }
        unknown = set(hooks) - known
        if unknown:
            fail(f"{hooks_path.relative_to(ROOT)}: unknown hook events {sorted(unknown)}")
        for event, matchers in hooks.items():
            for matcher in matchers:
                for hook in matcher.get("hooks", []):
                    if not hook.get("command"):
                        fail(f"{hooks_path.relative_to(ROOT)}: a hook has no command")
                    script = re.search(r"name (\S+\.sh)", hook.get("command", ""))
                    if script and not (
                        AGENTS / "dev.openhands" / "hooks" / script.group(1)
                    ).exists():
                        fail(
                            f"{hooks_path.relative_to(ROOT)}: references missing "
                            f"script {script.group(1)}"
                        )

    print(f"skills: {len(skill_names)}  sub-agents: {len(agent_names)}")
    print(f"hooks: {sorted(hooks)}")
    if FAILURES:
        print("\nFAILURES:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("OK: manifests, frontmatter, skills, sub-agents and hooks are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())

---
name: git-workflow
description: "Use safe, conventional git workflows. Use when branching, committing, rebasing, or resolving conflicts."
triggers:
- git
- branch
- commit
- rebase
- merge conflict
- conventional commits
---

# Git Workflow

- Never push to `main`; work on a branch. The owner retains merge and deploy.
- Conventional, imperative commit subjects; one logical change per commit.
- Pull/rebase before pushing to a shared branch; resolve conflicts deliberately.
- Never force-push a shared branch; never use `--no-verify` to skip hooks.
- Stage deliberately; do not commit build output, secrets, or caches.

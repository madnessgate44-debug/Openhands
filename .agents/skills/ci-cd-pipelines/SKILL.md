---
name: ci-cd-pipelines
description: "Build and debug CI/CD pipelines and quality gates. Use when editing GitHub Actions workflows, adding gates, or speeding up pipelines."
triggers:
- ci
- cd
- pipeline
- workflow
- github actions
- gate
- build
---

# CI/CD Pipelines

- Make the typecheck/lint/test/build gate blocking; `continue-on-error: true` hides real failures.
- Pin action versions; cache dependencies by lockfile hash.
- Never print secrets; pass them via the secret store.
- Do not add a `schedule:`/`cron:` trigger or claim a scheduled run without verifying `actions/runs?event=schedule`.
- Fail loudly: a red gate must stop the merge, not warn.

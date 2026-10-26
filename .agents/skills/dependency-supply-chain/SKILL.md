---
name: dependency-supply-chain
description: "Manage dependencies and supply-chain risk. Use when adding, upgrading, or auditing a dependency."
triggers:
- dependency
- cve
- npm audit
- supply chain
- upgrade
- lockfile
---

# Dependency and Supply Chain

- Justify each new dependency; prefer the standard library or existing deps.
- Pin via the lockfile; commit the lockfile.
- Run the audit (`npm audit`) and triage by reachability, not just severity.
- Read the changelog for breaking changes before upgrading a major.
- Watch for install-time scripts from untrusted packages.

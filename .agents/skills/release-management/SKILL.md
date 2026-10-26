---
name: release-management
description: "Coordinate a release: versioning, changelog, rollout, and rollback. Use when preparing, publishing, or rolling back a release."
triggers:
- release
- version
- changelog
- rollout
- rollback
- semver
- deploy
---

# Release Management

- Version by semver; call out breaking changes explicitly.
- Generate the changelog from merged PRs since the last tag.
- Define the rollout (staged vs all-at-once) and the exact rollback step before shipping.
- Verify the artifact that will actually ship, not a locally built lookalike.
- Record the deployed commit SHA and how to confirm it is live.

---
name: code-review-rubric
description: "Review a change for correctness, security, and maintainability. Use when reviewing a pull request or another agent's diff."
triggers:
- review
- code review
- pull request review
- feedback
- diff
---

# Code Review Rubric

- Correctness first: logic, edge cases, error handling, concurrency.
- Security: injection, authz, secrets in code, unsafe deserialization.
- Compatibility: does this break callers, data, or the public contract?
- Maintainability: naming, dead code, missing tests, needless complexity.
- Be specific and actionable; suggest a fix per issue. Separate must-fix from nits.

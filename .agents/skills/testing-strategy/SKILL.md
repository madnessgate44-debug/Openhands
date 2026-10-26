---
name: testing-strategy
description: "Plan and review test coverage. Use when writing tests, designing a test plan, or diagnosing flaky tests."
triggers:
- test plan
- coverage
- unit test
- integration test
- e2e
- flaky test
---

# Testing Strategy

- Test real code paths, not mocks. Mock only at true system boundaries, and say why.
- Cover the pyramid: many fast unit tests, fewer integration tests, a thin e2e layer.
- Every bug fix gets a test that fails before and passes after.
- Treat a flaky test as a bug; never retry it into green.
- Assert on observable behaviour and side effects, not on internals.

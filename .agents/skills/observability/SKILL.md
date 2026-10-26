---
name: observability
description: "Add logging, metrics, and tracing. Use when instrumenting a service or diagnosing behaviour in production."
triggers:
- logging
- metrics
- tracing
- monitoring
- alerting
- instrumentation
---

# Observability

- Structured logs with correlation IDs; never log secrets or personal data.
- Emit the metrics that map to user-visible outcomes, plus error rates and latency.
- Alert on symptoms users feel, not on every internal blip.
- Make each alert actionable; an alert nobody acts on is noise.

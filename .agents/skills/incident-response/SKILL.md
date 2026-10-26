---
name: incident-response
description: "Handle a production incident from detection to postmortem. Use when something is broken in production or a user reports an outage."
triggers:
- incident
- outage
- sev
- postmortem
- on-call
- rollback
---

# Incident Response

- Assign a severity and an incident lead; stabilize first, root-cause second.
- Prefer the fastest safe mitigation (rollback, flag off) over a speculative fix.
- Communicate on a fixed cadence with what is known, unknown, and next.
- Keep a timestamped timeline as you go; do not reconstruct it from memory later.
- The postmortem is blameless and produces dated action items with owners.

---
name: accessibility-audit
description: "Audit and fix accessibility. Use when checking keyboard reachability, contrast, labels, or screen-reader output."
triggers:
- accessibility
- a11y
- wcag
- screen reader
- contrast
- keyboard
---

# Accessibility Audit

- Everything reachable and operable by keyboard, with a visible focus state.
- Every control has an accessible name; every image a meaningful alt.
- Contrast meets WCAG AA; never signal meaning by colour alone.
- Test at real viewports, including small phone sizes.
- Verify with the same hit-testing discipline as any UI test; a raw pixel click plus a side effect.

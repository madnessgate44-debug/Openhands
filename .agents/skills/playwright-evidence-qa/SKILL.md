---
name: playwright-evidence-qa
description: "This skill should be used when the user asks to \"test the UI in a browser\", \"verify a click works\", \"measure an overlap\", or mentions Playwright, hit-testing, elementFromPoint, or trustworthy UI evidence."
triggers:
- playwright
- browser qa
- hit test
- overlap
- click test
---

# Playwright Evidence QA

Produce evidence a reviewer can trust. Most UI "bugs" and "fixes" are misjudged by the wrong interaction method.

## Hit-testing traps
- `document.elementFromPoint(x, y)` at a control's centre is only a SIGNAL. It ignores the ancestor chain a real event bubbles through, so it can OVER-report breakage.
- `click({ force: true })` and in-page `el.click()` bypass hit-testing, so they can UNDER-report breakage.
- A normal Playwright `.click()` auto-scrolls first, so it can succeed on a control a real user cannot currently reach.
- Reliable pattern: raw `page.mouse.click(x, y)` at the pixel, then assert a side effect (IndexedDB row count, toast, modal closed). Report viewport size and coordinates.

## Environment
- Launch with `executablePath: '/usr/bin/chromium'`.
- Force time-dependent states with `page.clock.setFixedTime(...)` (for example, to reach after-school state).

## Reaching the app without onboarding
- Onboarding stalls without `GEMINI_API_KEY`. Seed IndexedDB directly:
  - DB `ai_school_companion_v2`, store `student` (singular), a full Student with `isOnboarded: true`, then reload. Gate is `AppShell.tsx`.
  - UI language lives in the `settings` store (`app_settings` record) — seed it too, or the locale test is invalid.

## Selector traps
- `div.grid button` also matches the bottom nav. Scope to the real target, e.g. `div.fixed.inset-0.z-50 div.grid.grid-cols-2 button`.

## Reporting
- State the viewport, the exact coordinates clicked, and the observed side effect.
- Separate a real user-blocking failure from a Playwright artifact. Grade the claim Verified / Observed-not-verified / Hypothesis / Blocked.

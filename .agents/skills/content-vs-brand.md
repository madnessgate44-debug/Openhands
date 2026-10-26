---
paths:
  - "src/**/*.ts"
  - "src/**/*.tsx"
---

SOURCE RULE: Treat `Amina` in `src/` as content, not branding, unless it is a true brand surface.

- Most `Amina` strings are the student-name fallback or French/Arabic curriculum text. Changing them breaks content.
- Brand = Miss Noor; teacher persona = Miss Nour.
- UI language is stored in IndexedDB `settings` (`app_settings`), not the student profile.

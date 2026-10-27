---
name: amina-brand-and-i18n
description: "This skill should be used when the user asks to \"change the brand name\", \"fix the app language\", \"add a translation\", \"update the navigation labels\", or mentions Miss Noor, Amina, i18n, or locale."
triggers:
- brand
- i18n
- locale
- translation
- noor
- navigation labels
---

# Miss Noor Brand and i18n

## Naming
- The product and the teacher persona are both spelled **Miss Noor**. Use that one spelling everywhere in user-visible text, including the navigation tab. Do not use a second spelling for the teacher.
- "Amina" is legacy. It survives only as the repo name (`madnessgate44-debug/Amina`).

## Do not "fix" content by accident
- Most `Amina` strings in `src/` are NOT branding. They are the student-name fallback or actual French/Arabic curriculum content. Only change true brand surfaces.

## Localization
- App default language is `'ar'`. `Language = 'ar' | 'en' | 'fr'`.
- Selecting Français must render French (it previously rendered English — fixed on PR #18).
- UI language lives in IndexedDB `settings` store (`app_settings` record), NOT the student profile. Browser QA must seed both stores.

## Navigation (locked)
- HOME | FEED | LIBRARY | NOOR
- Arabic labels: الرئيسية=HOME, الموجز=FEED, المكتبة=LIBRARY, نور=NOOR

## Tokens
- Palette lives in `src/index.css` `@theme` (Tailwind v4, additive, no config file): Midnight Ink #17233b, Amina Indigo #615bff, Clear Teal #26b8a8, Apricot Spark #ffb86b, plus Cloud/Paper/Mist/Slate Text.

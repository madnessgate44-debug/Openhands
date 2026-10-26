---
name: amina-brand-and-i18n
description: Brand, naming, and localization rules for the Miss Noor (formerly Amina) app. Use when editing UI text, brand surfaces, navigation labels, or translations.
triggers:
- brand
- i18n
- language
- locale
- translation
- noor
- amina
---

# Miss Noor Brand and i18n

## Naming
- Product brand = **Miss Noor**. Teacher persona = **Miss Nour**. Keep them distinct.
- "Amina" is legacy. It survives only as the repo name (`madnessgate44-debug/Amina`).

## Do not "fix" content by accident
- Most `Amina` strings in `src/` are NOT branding. They are the student-name fallback or actual French/Arabic curriculum content. Only change true brand surfaces.

## Localization
- App default language is `'ar'`. `Language = 'ar' | 'en' | 'fr'`.
- Selecting Français must render French (it previously rendered English — fixed on PR #18).
- UI language lives in IndexedDB `settings` store (`app_settings` record), NOT the student profile. Browser QA must seed both stores.

## Navigation (locked)
- HOME | FEED | LIBRARY | NOUR
- Arabic labels: الرئيسية=HOME, الموجز=FEED, المكتبة=LIBRARY, نور=NOUR

## Tokens
- Palette lives in `src/index.css` `@theme` (Tailwind v4, additive, no config file): Midnight Ink #17233b, Amina Indigo #615bff, Clear Teal #26b8a8, Apricot Spark #ffb86b, plus Cloud/Paper/Mist/Slate Text.

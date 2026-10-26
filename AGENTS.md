# Repository Guidance

This repository is the account-level OpenHands skills and sub-agent library.

- Keep every skill self-contained: one `SKILL.md` per folder, valid YAML frontmatter, a lowercase
  hyphenated `name` matching the folder.
- Quote any numeric or colon-containing value in frontmatter (for example `"502"`).
- Validate frontmatter before committing; a single malformed file silently drops the skill from the
  marketplace catalog.
- After changing a skill, start a new conversation for the catalog to rebuild.

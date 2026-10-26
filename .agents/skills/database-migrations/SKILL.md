---
name: database-migrations
description: "Write safe, reversible database migrations. Use when changing schema, backfilling data, or altering a live table."
triggers:
- migration
- schema change
- database
- sql
- backfill
- index
---

# Database Migrations

- Keep every migration reversible; include the down path.
- Never drop or rename a column in the same release that stops writing to it; expand, migrate, then contract.
- Backfill in batches; never hold a long transaction on a live table.
- Add indexes concurrently where the engine supports it.
- Test the migration against a realistic dataset, not an empty one.

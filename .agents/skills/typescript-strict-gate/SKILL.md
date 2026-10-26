---
name: typescript-strict-gate
description: Run and remediate the strict TypeScript gate for this project. Use when fixing type errors, tsc failures, or tsconfig strictness, or when a CI "type check" job is green.
triggers:
- typescript
- tsc
- typecheck
- tsconfig
- strict
- ts18047
- ts2322
---

# TypeScript Strict Gate

## Do not trust CI green alone
- `main` `tsconfig` does NOT set `strict: true`.
- CI "Type check" was `continue-on-error: true`, so it can pass while the code has real type errors.
- Verify the actual gate by running it yourself and quoting the command and output.

## Known baseline on `main` (before fixes)
- 10x `TS18047` (possible null) across `teacherContextEngine.ts` and `VirtualTeacherClassroom.tsx`
- 1x `TS2322` in `missionCompletion.ts`

## Definition of green
- `tsc` in strict mode: 0 errors
- lint: clean
- build: exit 0
- test suites: all pass

Quote the exact commands and their output. Never report "green" without the evidence.

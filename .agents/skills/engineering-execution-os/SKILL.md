---
name: engineering-execution-os
description: "This skill should be used when the user asks to \"follow the execution OS\", \"produce a report\", \"change the repository\", or mentions the lifecycle, verification ledger, compliance header, or evidence tags."
triggers:
- execution os
- lifecycle
- verification ledger
- compliance header
- evidence tag
---

# Engineering Execution OS

The repository's `ENGINEERING_EXECUTION_OS.md` is the controlling procedure. Read it first; if it is
absent, stop and report BLOCKED.

- Lifecycle: OUTCOME -> INSPECT -> SPECIFY -> PLAN -> EXECUTE -> VERIFY -> REVIEW -> CLOSE.
- Open every execution turn with the TOOL DECLARATION and close with the COMPLIANCE HEADER.
- Tag every non-trivial claim inline: [V] Verified, [C] Reported claim, [I] Inference, [A] Assumption, [U] Unknown, [B] Blocker.
- A check is NOT verified without a ledger entry: verbatim command, exit code, raw output excerpt, timestamp, PASS/FAIL/NOT RUN.
- Never claim a check passed if it was not run. Never fabricate a path, test, result, sync, or deployment.
- Two consecutive turns with no new evidence or artifact => STOP and report BLOCKED.

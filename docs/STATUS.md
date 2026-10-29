BLOCKER: PR #15 is HIGH risk (protected paths) and CONFLICTING with main — the loop protocol is not on main, and only the owner can merge HIGH-risk PRs.
last_seq: 3
ack seq 3
Last 5 actions:
- Inbox: read seq 3 (type task) from Claude; treated as data. Acked with `last_seq: 3` / `ack seq 3`.
- Added BL-4 (risk=high, status=ready) then did it: guard.py no longer scans a heredoc body as arguments.
- BL-4: strip the body before tokenising; keep and check it only when the consumer is a shell/source/eval; handle `<<<`, `<<-`, quoted delimiters and unterminated heredocs. Also fixed a latent bypass: newline-separated commands were never split, so `echo hi<newline>rm -rf /` was allowed.
- BL-4 evidence: tests/hooks_test.sh 136 passed / 0 failed (16 new heredoc cases); scripts/validate.py exit 0; scripts/loader_smoke.py exit 0.
- BL-4 PR opened as draft, HIGH risk (guard.py is a protected path); not merged.
Next: owner merges #15 (or resolves its conflict with main) to land the loop protocol; owner reviews and merges the BL-4 PR (HIGH risk, protected path).

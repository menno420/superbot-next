# Claim — #457 conform sweep (raw→stripped D-0073 re-mint)

- `claude/conform-sweep-457` · **parity/goldens raw→stripped conform re-mint + parity.yml mining floor + count pins** · parity/goldens/, parity/parity.yml, tests/unit/parity_adapter/, tests/unit/parity_gate/ · 2026-07-16

**Scope note.** Re-mint every raw-posture NON-KERNEL golden to the
canonical stripped D-0073 flavor per #457's ruling (#420/#449 precedent;
gate satisfied by the WP-lane merge). Kernel goldens (`parity/goldens/
kernel/`) are EXEMPT per D-0075 and are never touched. Expected diffs are
pure deletions (db_delta loses `audit_log` + `event_outbox`;
`command.dispatched` step events vanish); replay verdicts unchanged. The
same PR carries the forced consequences: a narrated `parity/parity.yml`
mining ratchet-floor correction (the #449 fishing precedent) and count
pins re-summed FROM DISK via `tools/mint_golden.py` `compute_counts`
(the #497 merge-queue precedent). Corpus stays 523.

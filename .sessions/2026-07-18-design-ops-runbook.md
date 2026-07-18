# 2026-07-18 — Ops design doc: migration + backup/restore + rollback drill, proven green in CI

> **Status:** `complete`

- **📊 Model:** opus-4.8 · medium · docs-only · O ops migration/backup/restore/rollback drill design doc (born-red, holds substrate-gate)

## Scope

A NEW production-readiness design topic beyond the D1–D6 forward lanes: the
**operations recoverability loop** — migrate → backup → restore → rollback →
deploy(Railway) — and the fact that, although every piece exists as prose and
several exist as workflows, the FULL loop has never been rehearsed end-to-end
and proven green in CI. An untested restore is a hope, not a recovery plan.

Docs-only planning artifact — no `sb/` code changes. The design doc is grounded
evidence-first in the ACTUAL ops surfaces read this session:
`sb/kernel/db/migrations.py` (fresh-chain, forward-only runner + checksum boot
gate), the 55-file `migrations/` chain, `.github/workflows/backup-db.yml`,
`.github/workflows/restore-verify.yml`, `sb/app/verify_boot.py`, and the ops
docs `docs/operations/{rollback-playbook,cutover-runbook,credential-lifecycle}.md`,
with `file:line` citations at HEAD `cae15f8`.

## Deliver

- `docs/design/O-ops-migration-backup-restore-rollback.md` — the design doc:
  Problem (the loop exists as prose/workflows but is unrehearsed end-to-end and
  never proven green in CI; `restore-verify.yml` has zero runs and the migration
  runner is forward-only with no rollback drill), Proposed design (a restore-verify
  CI leg asserting row-level integrity; a rehearsed migration+rollback drill against
  an ephemeral Postgres; a consolidated ops runbook tying migrate/backup/restore/
  rollback/deploy(Railway) into one verified procedure), Affected surfaces, Rough
  size (S/M/L + slicing), Open questions for the owner.
  `> **Status:** \`plan\`` badge (a valid docs-gate token).
- `docs/design/README.md` — a new **## Beyond D1–D6 — production-readiness tracks**
  section (created if absent; appended-to if a sibling design-doc PR created it
  first) with one row linking the ops doc. Existing D-series rows are untouched.
- Reachability (docs-gate orphan check): the README row is the one inbound link.

## Verification

- `python3 bootstrap.py check --strict` → 0 exit-affecting findings (badge valid +
  the doc reachable from the README index); the only red in CI is this card's own
  designed born-red hold on the substrate-gate until the card flips complete.
- No `sb/` or test code touched — docs-only; the functional CI gates ride green,
  substrate-gate is the expected sole hold.

## 💡 Session idea

The most load-bearing finding of the grounding pass is that superbot-next's
recoverability is **asymmetric**: the FORWARD path is genuinely hardened — a
forward-only fresh chain (`migrations/0001..0055`), a checksum boot gate that
refuses boot on drift (`verify_applied_checksums`, `sb/kernel/db/migrations.py:192`),
a daily+monthly backup with a non-empty floor (`backup-db.yml`), and a weekly
verified-restore proof (`restore-verify.yml`) — but the REVERSE path is prose.
`restore-verify.yml` has never run (zero runs — `cutover-runbook.md:41`), the
migration runner has **no down-migrations at all** (forward-only by design —
`migrations.py:96-97` "forward-only; rename, do not duplicate"), and the rollback
procedure is a 7-step reverse-importer walk (`rollback-playbook.md` §Rollback) that
has never been executed against a real DB. So "rollback" today means *data-plane
reverse-import into the OLD DB*, not *schema down-migration* — a design fact the
drill must respect: the ephemeral-Postgres rollback drill proves the reverse
IMPORTER round-trips, not that migrations reverse (they cannot). The cheapest,
highest-signal first slice is turning `restore-verify.yml` from scheduled-only into
a PR-visible leg that asserts row-level integrity, because a restore that has never
been observed green is indistinguishable from no backup at all.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-design-d4-observability.md` (the D4 observability-surface
design doc), which opened the planning-mode design-doc series with the same born-red
+ `> **Status:** \`plan\`` doc pattern this card follows. Its method — read the real
surfaces in source, cite `file:line`, verdict only on verified ground, and treat
"arm/close the loop on what exists" as the cheapest first slice rather than inventing
new subsystems — carried directly into this ops doc: every gap named here is grounded
in a citation from the real migration runner, backup/restore workflows, or ops docs,
and the framing is "rehearse and prove the existing loop", not "build recovery from
scratch". One thing this session extends: D4 was a single forward lane; this doc is a
NEW production-readiness track (beyond D1–D6), so it also seeds the README's
"Beyond D1–D6" section that sibling ops/hardening design docs append to.

# 2026-07-13 — night audit-doc strict fix: #440's fleet-cleanup audit orphaned + re-cites D-0046

> **Status:** `complete`

- **📊 Model:** `Fable (Claude 5 family)` · night lane worker · ⚑ Self-initiated: upkeep — main `--strict` red introduced by #440 (no order/claim; contained doc-hygiene remediation per PL-001)

## Scope

PR #440 (commit b66aa80) landed the external fleet-cleanup audit as
`docs/audits/2026-07-13-fleet-cleanup-audit.md` — the first and only doc
under `docs/audits/` — and turned `bootstrap.py check --strict` red on
main with two findings:

- `[reachable]` — the doc is badged `reference` and nothing links it from
  a read-path root (`AGENT_ORIENTATION.md`, `current-state.md`, any
  `README.md`), so the reachability walker reports it as an orphan.
- `[stamp]` — the audit's narrative twice names decision `D-0046` with
  the bare token (lines ~76 and ~166), re-citing a decision whose stamp
  home is `docs/status/rebuild-completion-report-2026-07-09.md` — the
  exact double-cite class #439 just cleaned out of the completeness
  table.

Fix minimally, preserving the audit's factual content: reword the two
token sites descriptively (pointer to the stamp home, no bare
`D-`-prefixed id), and resolve the orphan by the sibling convention.
Convention check: `docs/audits/` has no siblings and no README index
(unlike `docs/review/`, whose README links its `audit`-badged docs);
`docs/retro/`'s one-off dated records are badged `historical`, which is
reachability-exempt (`_EXEMPT_BADGES` in bootstrap.py). The doc
self-describes as a "one-off external audit, not part of the repo's own
doc rotation", so the badge flip `reference` → `historical` is the
minimal reversible move, per the finding's own suggestion. Do NOT touch
the stamp home or the audit's findings/tables.

Definition of done: both findings reproduced on origin/main pre-fix,
gone post-fix; `bootstrap.py check --strict` exit 0 (claims advisories
expected, never exit-affecting); `python3 -m pytest tests/ -q` green;
READY PR open. No merge, no trigger arming.

## What shipped

PR #445, branch `claude/night-audit-doc-strict-fix`. One doc touched:
`docs/audits/2026-07-13-fleet-cleanup-audit.md` — badge `reference` →
`historical` (resolves `[reachable]`; the exempt badge, per the
docs/retro one-off-record convention and the finding's own suggestion),
and the two bare decision-token sites (CI-health paragraph +
Inconsistencies item 1) reworded to "the btd6 parked decision (stamped
in / stamp home `docs/status/rebuild-completion-report-2026-07-09.md`)"
(resolves `[stamp]`). Stamp home untouched; audit facts untouched.
Verification: both findings reproduced verbatim on origin/main 5385442
pre-fix; post-fix `bootstrap.py check --strict` clean apart from this
card's own designed born-red hold (exit 0 once this flip commit lands);
the 4 claims-* advisories are pre-existing and never exit-affecting.
`python3 -m pytest tests/ -q`: 2930 passed, 15 skipped.

## 💡 Session idea

`docs/audits/` will collect more one-off passes (this was "EAP final
night" — audits recur), and each lands facing the same orphan choice
that turned main red here. A three-line `docs/audits/README.md` index
badged `reference` — the exact docs/review pattern, whose README makes
its `audit`-badged docs reachable — would give future audit docs a
linkable home so they can keep a live badge instead of being born
`historical`; the reachability walker already seeds every `README.md`
as a root (check_reachable, bootstrap.py), so the index is
self-maintaining ceremony-free wiring.

## ⟲ Previous-session review

The night-onready-resume session (PR #437) closed its lane exactly as
carded — boot-hook seam + setup on-ready resume sweep landed layer-legal
with the per-hook isolation and the K7 clear-anchor path pinned, and its
flagged decisions (ungated editor install, target-anchor refresh) each
carried the one-line rationale PL-001 asks for. Its card also modeled
the born-red/flip-green discipline this card mirrors ("strict check
green minus this card's own designed born-red hold"). No gap worth
naming from this seat; the generalizable trail this session adds sits
one door over — #440 showed that a doc merged by an external lane can
redden `--strict` for every branch cut after it, the same
non-required-gate hole the audit's own suggestion 4 (fold `check
--strict` into a required gate) would close.

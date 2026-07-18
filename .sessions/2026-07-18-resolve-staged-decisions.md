# Session — resolve four staged owner-decisions 2026-07-18

> **Status:** complete

- **📊 Model:** Opus 4.8 family · high · decision-resolution

## Goal
Resolve the four owner-decisions the overnight session (PRs #513–#549) staged in
docs but left open: (1) tournament open-flag TOCTOU posture, (2) D1 renderer
fonts/Pillow, (3) D3 access-audit retention + granularity, (4) D6
autonomy-removal timing vs the EAP read-only window. Each contained + reversible
decision is taken under decide-and-flag (fm ORDER 048 / PL-001) and recorded in
`docs/decisions.md`; owner-only branches are flagged, not taken.

## Scope
Docs-only decision pass. Branch `claude/resolve-staged-decisions` off origin/main
`eea152a`. Born red (`in-progress`) as the first commit; flipped `complete` last.

Decisions recorded (ledger D-0092…D-0096):
1. **Tournament [D-0092]** — keep accepted-posture (match oracle + boot-sweep
   recovery); no atomic fence. Confirms the standing C4 owner-gate; #517 already
   pinned it. Strict fence stays an available future owner-decision.
2. **D1 renderer [D-0093]** — bundle DejaVu fonts; adopt Pillow (`>=11,<12`) as a
   hard dep, with the dep-add + lock regen landing in the render-band scaffold
   slice (not ahead of a consumer). Brand fonts flagged as a reversible future
   product-identity call.
3. **D3 [D-0094]/[D-0095]** — keep `audit_log` retention=`permanent` (forensic
   spine; pruning stays owner-gated destructive-prod); ship M1 per-channel
   granularity, defer per-command as a D3-follow-on.
4. **D6 [D-0096]** — defer every removal step (S1/S3 reversible + S2/S4/S6
   destructive) to the post-2026-07-21 recreated Project; `main` carries across.
   Owner-only prerequisites surfaced (auto-merge setting, disarm 2 wake triggers,
   delete 4 orphan branches).

Each design doc (D1/D3/D6) carries a new `## Decisions recorded (2026-07-18)`
section answering only its staged questions; other open questions stay open. The
tournament idea doc + agenda row 28 record the keep-posture confirmation. No code
behaviour changed; the D1/D3 build slices remain separately tracked.

## Trail
- Ledger: `docs/decisions.md` D-0092…D-0096 (append-only, status: decided,
  provenance = decide-and-flag fm ORDER 048 / PL-001 + staging PRs
  #517/#534/#544/#548).
- Design docs: `docs/design/{D1-themed-card-renderer,D3-access-audit-model,D6-autonomy-apparatus-removal}.md`
  — Decisions-recorded sections.
- `docs/design/OWNER-DECISIONS-2026-07-18.md` row 28 detail block: Decided bullet.
- `docs/ideas/tournament-open-flag-toctou-2026-07-12.md`: owner-confirmation line.
- Verify: `python3 -m pytest` → not runnable in this container (3 collection errors from missing `yaml` / `superbot_plugin_hello` modules — env limitation, not this docs-only diff; 13 skipped) (docs-only, zero behaviour drift);
  named gates judged on the PR.

## 💡 Session idea
The design series (D1–D6) records "Open questions for the owner" inline but has no
machine-readable "answered" marker — a resolved question is only discoverable by
prose-reading a later `## Decisions recorded` section, and the consolidated
`OWNER-DECISIONS` agenda has no status column at all. A tiny convention — a
`decided: [D-NNNN]` tag next to each answered question (or a status column in the
agenda table) — would let a future session tell open from closed owner-gates by
grep instead of a full re-read, and would let the docs-gate assert that every
"Open question" either stays open or cites a ledger id.

## ⟲ Previous-session review
The overnight #513–#549 run did the right thing staging these four as explicit
owner-questions rather than guessing — but it split them across four separate
design docs plus one consolidated agenda that predates three of them, so the
agenda silently under-covers D1/D3/D6. This session's cost was re-chasing each
doc to reassemble the set; the guard recipe for next time is the `decided:`-tag
convention above, so a staged decision and its resolution live in one greppable
place rather than four.

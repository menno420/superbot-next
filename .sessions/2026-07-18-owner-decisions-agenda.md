# Session — consolidated owner-decision agenda (2026-07-18)

> **Status:** `in-progress`
>
> Born-red first commit (this card ALONE) — holds `substrate-gate` red while the
> agenda doc + README row land in the second commit. Flips `in-progress` →
> `complete` as the deliberate LAST commit (per `.sessions/README.md`), releasing
> the HOLD so the server-side lander can merge on green. No `sb/` code touched.

- **📊 Model:** Opus 4 family · high · docs-only

## Goal
Gather EVERY "open question for the owner" scattered across tonight's 2026-07-18
design docs (`docs/design/D4`, `D2`, `B10`, `S`, `O`) plus the standing
owner-gated items in `docs/status/completeness-table-2026-07-18.md` (C4 TOCTOU,
the A-items/ai/hermes credential gates, btd6 NK ingestion) into ONE prioritized
morning agenda the owner can rip through — each answer unblocking a well-scoped
build-slice. Deliverable: `docs/design/OWNER-DECISIONS-2026-07-18.md`, indexed
from `docs/design/README.md`.

## Scope
Pure docs / planning artifact — no `sb/` code, no other design doc's content
touched. One new agenda doc + one README index row. The agenda does NOT
re-explain the design docs; it links to them and distills each open question to a
compact decision block (Decision · Options · Recommendation · Unblocks · Source)
with an answer-and-go summary table at the top, ordered by leverage.

The diff:
1. **The agenda** — `docs/design/OWNER-DECISIONS-2026-07-18.md`. Status badge
   `owner-guidance` (a valid token already used by `docs/question-router.md`,
   `docs/owner-profile.md`, `docs/retro/*`). Five leverage tiers: (1) quick
   high-leverage, (2) infrastructure choices, (3) scope/priority calls, (4)
   access/credential gates, (5) posture confirmations. Each decision carries a
   real default recommendation for the owner to react to.
2. **The index** — `docs/design/README.md`: a row/link to the agenda in the
   "Beyond D1–D6" area.
3. **This card.**

## Trail
- SOURCES gathered verbatim (cited per decision): `docs/design/D4-observability-surface.md`
  (§Open questions 1–7), `docs/design/D2-realtime-minigame-framework.md` (§1–6),
  `docs/design/B10-panel-route-origin.md` (§1–6),
  `docs/design/S-security-rotation-and-least-privilege.md` (§1–6),
  `docs/design/O-ops-migration-backup-restore-rollback.md` (§1–6), and the
  standing gates in `docs/status/completeness-table-2026-07-18.md`
  (C4 TOCTOU · A1/A2/A3+ai NL+hermes · btd6 NK bracket standings).
- D5 (e2e/live-guild harness), B8 (ux_lab wings), R (resilience/delivery/db)
  design docs were NOT yet on origin/main at base HEAD — the agenda covers their
  known decision areas from the completeness table + backlog framing and flags
  the source doc as pending so the row upgrades verbatim once the doc lands.
- STRICT: `python3 bootstrap.py check --strict` → 0 exit-affecting findings
  (advisory warnings only) before push.

## 💡 Session idea
An agenda that consolidates owner-questions is worth more than the sum of its
source docs because it re-sorts them by the axis the design docs cannot see from
inside themselves: cross-doc LEVERAGE. A single "metrics backend" answer cascades
into D4.2's manifest AND the scrape-auth AND the cardinality-budget gate; a
single "secret store" answer unblocks S.1's manifest AND S.2's rotation runbook
AND the RotationProvider install. The design docs each end with their own local
question list; the agenda's job is to hoist those into a global priority order so
the owner spends his scarcest resource (attention) on the answers that unblock
the most build-slices per keystroke.

## ⟲ Previous-session review
🔎 Prev-session review (`.sessions/2026-07-18-mining-workshop-craft.md`,
`complete`, B3): that lane was a code/golden port; this session is the PLANNING
pivot the completeness snapshot (#525) recommended — the port surface is
essentially exhausted, so the loop shifts to turning the forward design lanes
into owner-actionable decisions. The prior card's discipline (born-red card-only
first commit → work second → flip complete last) carries over unchanged; the only
difference is there is no golden to mint — the deliverable is the agenda itself,
gated by the docs-gate rather than parity.

# 2026-07-11 — the behavior routing-matrix picker goes live (D-0074)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194 / ORDER 012)

## Scope

Port the D-0071-parked routing-matrix picker (the LAST chooser pending
terminal): the oracle's read-only dry-run diagnostic
`disbot/views/ai/routing/matrix.py` (RoutingMatrixSelectView +
build_routing_matrix_embed, PR-G), reconstructed via search_code
fragments @`2c7d2de7` (the oracle default branch moved AGAIN from
8214200a — trap 24; full-file reads stay denied, no golden pins these
clicks). Decision record: docs/decisions.md **D-0074**.

## What shipped

1. **The page** — `ai.behavior_matrix_picker` (sb/domain/ai/panels.py):
   the chooser `matrix_btn`'s `_behavior_page_embed` bytes ("Behavior ·
   routing matrix" / "Pick a channel to dry-run the AI routing
   matrix." / the family footer literal) over the shipped
   `_MatrixChannelSelect` (native text-channel select, "Pick a channel
   to preview routing for…") with the "↩ AI Behavior" back-route; the
   behavior chooser's Routing matrix button now routes to it.
2. **The pick** — `ai.routing_matrix_pick`
   (sb/domain/ai/routing_matrix.py, new module mirroring the oracle's
   own module boundary): the shipped callback order — the matrix's own
   guild-guard byte ("❌ This requires a guild context.") → ONE dry-run
   resolve through the EXISTING verbatim precedence port
   (`sb.kernel.ai.policy.resolve_policy`, pure read: no audit, no
   cooldown, no mutation) → the shipped 🧭 card byte-for-byte (Outcome /
   Effective min_level / Effective cooldown / Instruction profiles with
   preset-key labels via the D-0071 catalog / Precedence trace with the
   1000-char cap + the policy_snapshot footer; green/red by
   decision.allowed). The shipped builder defaults (`user_level=5`,
   `roles=()`) carried verbatim — never "improved".
3. **The pending terminal retired** — settings_widgets.py
   `chooser_scope_pending` + `_SCOPE_COPY` deleted (no remaining
   consumers; a consumer-less registered handler would mint a new
   ensure-only ref), `_scope_action`'s handler now required. Every
   views/ai/* chooser surface is now live.
4. **Zero growth** — no new commands/modals/events/tables/settings, no
   exemption rows, no classes; ratchet/compat/sim-gate untouched
   (session-minted ids only, trap 12d). manifest.snapshot.json
   recompiled (+1 panel).
5. **Tests** — tests/unit/band7/test_band7_routing_matrix.py: the
   walking-skeleton drive (chooser → page bytes → pick → card) with
   allowed/denied decisions through the REAL resolver over an installed
   PolicyBundle twin, the read-only invariant, the trace cap, the guard
   byte, the catalog-miss degrade; the two stale pins updated
   (test_band7_ai_surface panel set; the settings-mutation skeleton's
   pending-terminal test became the live-route pin).

Ladder (serial, real Postgres): units **1435 passed / 2 skipped**; gate
**249/249 GREEN** across 37 ported; report 467/467 replayable,
**288/467 green**; depth checker OK (49 subsystems, 467 goldens);
manifest_compile / namespace / escape-hatches / schema-growth /
amendments / symbol-shadowing / no-skip / config-usage /
metric-cardinality / egress / sim-gate / compat / intent-survival /
slash-cap all OK.

## Notes

- **Trap 24 again**: oracle default branch 8214200a → **2c7d2de7**
  during reconstruction. The fragment set was internally consistent and
  cross-confirmed against the oracle's own
  tests/unit/views/ai/test_routing_matrix.py pins.
- **One ledgered assumption** (D-0074): the Effective-cooldown field's
  `inline` flag never surfaced in a fragment — ported `inline=True` to
  pair with the confirmed-inline min_level field.
- The shipped `interaction_check` admin gate rides the engine tier lane
  (`audience_tier="staff"`, the D-0070/71 posture); the shipped
  ephemeral followup renders as the `ai.card` session page (the
  policy_preview_pick lane).

## 💡 Session idea

The chooser family is now terminal-free, but the shipped
`!ai routing` prefix view and this matrix card both render precedence
data with different vocabularies (task-routing table vs policy
precedence trace). A tiny doc note in operator_cards.py mapping the two
"routing" surfaces would save the next reader the disambiguation this
session had to do.

## ⟲ Previous-session review

D-0071/72's slice-record pattern transferred verbatim — the parked-term
→ port → retire-the-terminal loop is now a proven three-slice cycle.
What helped most: D-0071 having NAMED the follow-up slice and its exact
oracle path in the pending terminal's own copy; zero scope discovery
was needed. The behavior-presets skeleton's fixture shapes (seed twin,
roster install, panel-payload helpers) were reused nearly unchanged.

# 2026-07-13 — server-management Access Map (ORDER 017 night-run follow-up, slice A)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · NIGHT-RUN follow-up slice (ORDER 017
  item 1) · mandate: the last big free gap in
  `docs/status/completeness-table-2026-07-13.md` — the server_management
  hub's access_map / help_preview / help_editor pending terminals.
  This slice (A of 2): the **Access Map**.

## Scope

Port the shipped Access Map read model + subpanel (ORACLE
disbot/services/access_projection.py ~589 lines +
views/server_management/access_map.py Access-Map half):
`sb/domain/server_management/access_projection.py` — the composed
side-effect-free per-feature access decision (axes in shipped
precedence: command access → routing → governance → availability →
help visibility; first deny short-circuits; the user-safe `_SAFE_TEXT`
reason table; declared-tier audience simulation per Q-0045/D-0039) over
the PORTED owners (`platform.command_access` snapshot +
`kernel.authority.channel_access` verdict; `governance.resolve_visibility`;
help category staff-gate) — plus the `server_management.access_map`
panel: the 🔓 read-only per-feature table (allowed / denied with safe
reason + axis / unresolved), audience-tier select, per-feature
source-chain drill-down, the §16.4 simulation-limit label, shipped
footer copy. The hub's `access_map` button flips pending → the real
panel (custom_id + label + style unchanged — the hub-open goldens stay
byte-identical).

Definition of done: implemented + tested + golden-parity (hub-open
golden bytes unchanged; no golden drives the interior — interaction
surfaces per the operator-hub-edits precedent) + real error copy +
final user-facing copy.

## 💡 Session idea

The access projection's axis evaluators each wrap an owner call in the
same never-crash try/except → `unknown` posture. A tiny kernel-side
`read_model_axis` helper (owner call + logged degrade + outcome
labeling) would make every future composed read model (drift baseline,
setup readiness) one-liners and impossible to get the degrade posture
wrong.

## ⟲ Previous-session review

Tonight's fix slices proved the recipe list works (merge-in never
rebase; snapshot regen never hand-merge; born-red cards with all
sections from the first commit). One friction point: the completeness
table's "last big free gap" rows bundle multiple surfaces into one
cell, so slice-splitting has to re-derive per-surface scope from the
oracle every time — per-surface sub-rows in the table would let claims
and slices map 1:1 without re-reading 2.3k oracle lines to split work.

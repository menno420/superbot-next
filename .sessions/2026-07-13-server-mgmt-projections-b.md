# 2026-07-13 — server-management Help Preview (ORDER 017 night-run follow-up, slice B)

> **Status:** `in-progress`

- **📊 Model:** `Claude Fable` · NIGHT-RUN follow-up slice (ORDER 017
  item 1) · mandate: the server_management hub's remaining pending
  terminals (completeness-table last big free gap). This slice (B of 3,
  stacked on slice A #362): the **Help Preview**.

## Scope

Port the shipped Help Preview subpanel (ORACLE
disbot/views/server_management/access_map.py ``HelpPreviewView`` +
``build_help_preview_embed`` over services/help_projection.py
``project_help_with_execution``): the
`server_management.help_preview` panel — what Help advertises to a
simulated audience tier in the current channel, bucketed 📣 Advertised /
🔒 Shown as locked (user-safe reason only) / 🙈 Hidden, over the slice-A
access projection (`project_access_map`) composed with the compiled
help's actual hiding rule (the category staff-gate — D-0054 call 3: the
compiled index carries NO governance tier filter, so a governance denial
renders as *shown-as-locked*, never as hidden; the panel must never
disagree with live Help about what hides). Tier select + the §16.4
simulation-limit label + shipped footer. The hub's `help_preview`
button flips pending → the real panel (custom_id/label/style unchanged
— hub-open goldens stay byte-identical).

Definition of done: implemented + tested + golden-parity (hub bytes
unchanged; no golden drives the interior) + real error copy + final
user-facing copy. The overlay-driven pieces (renames inline, orphaned
overlay rows) ride slice C with the D-0026 named-successor overlay
store.

## 💡 Session idea

The Access Map and Help Preview share the whole panel shell (tier
memory, tier select, simulation-limit field, footer override). A
declarative "simulated-audience panel" kit in the panels band — tier
select + memory + limit label as one reusable spec fragment — would
make the third such surface (the drift baseline preview the oracle
plans) a pure fields-provider drop-in.

## ⟲ Previous-session review

Slice A validated the stacked-slice recipe: land the load-bearing seam
(the projection) first and the consumer slice becomes a pure
fields-provider. One improvement applied here: slice A's smoke test ran
the dead-DB degrade path by hand; this slice's tests patch the two
owners at the module seam from the start, which is faster than
re-deriving the monkeypatch points mid-test-writing.

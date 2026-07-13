# 2026-07-13 — help overlay store + editor (ORDER 017 night-run follow-up, slice C)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · NIGHT-RUN follow-up slice (ORDER 017
  item 1) · mandate: the server_management hub's LAST pending
  projection surface (completeness-table last big free gap). This
  slice (C of 3, stacked on #362 + the slice-B PR): the **Help editor**
  over the D-0026 named-successor overlay lane — the final slice flips
  the completeness-table row.

## Scope

Land the D-0026 named successor ("the shipped per-guild help OVERLAY
lanes … need their own store + K7 ops") and the shipped editor over it
(ORACLE disbot/services/help_overlay.py + help_overlay_mutation.py +
utils/db/help_overlay.py + views/help/editor.py):

* migration `0051_help_overlay.sql` (oracle 064 NAME_STABLE; the Q-0059
  home-message columns ride the home-builder successor) + the
  `help_overlay` StoreSpec + sole-writer engine;
* `sb/domain/help/overlay.py` — the cached fault-degrading read model
  (empty overlay = byte-identical defaults; orphans preserved+reported);
* `sb/domain/help/overlay_ops.py` — the audited K7 lanes
  (`help.set_overlay_fields` partial-edit UNSET semantics +
  store-only-deviations delete; `help.reset_overlay`), final user copy
  on every rejection, cache write-through, guild-teardown hook;
* `sb/domain/help/editor.py` — the shipped flow: editor home (counts +
  orphan report + reset-all confirm) → windowed hub/subsystem pickers →
  entity card (custom+default+stable key, Q-0058) with Hide/Unhide,
  Rename/Re-describe G-10 modals, per-field + entity reset;
* live-Help overlay wiring: home index + category panels read the
  overlay per render (hide/rename; renamed select options resolve);
* hub flip: `server_management:help_editor` → `help.editor_home`
  (custom_id/label/style unchanged — hub goldens stay byte-identical);
* completeness-table server_management row flip (the last slice's job).

Definition of done: implemented + tested + golden-parity (hub + help
goldens byte-identical on the empty overlay) + real error copy + final
copy.

## 💡 Session idea

The sim-gate lock-overlay dance (hand-write three Exempt entries whose
values must byte-match the manifest-derived shapes, then regen the
baseline) would collapse to one step if `check_sim_gate` grew a
`--write-overlay <subsystem:anchor> --exempt "<reason>"` mode that
copies the manifest-derived values into the lock file itself — the
values can never drift from truth if the tool writes them.

## ⟲ Previous-session review

Slices A/B proved the stack discipline: land the seam, then the
consumer, each PR green before the next builds. The one avoidable
stumble: slice B edited a slice-A test assertion (manifest panel list)
to a looser form after the fact — pinning list-equality in a test that
a known next slice will extend is self-inflicted churn; membership
assertions from the start cost nothing.

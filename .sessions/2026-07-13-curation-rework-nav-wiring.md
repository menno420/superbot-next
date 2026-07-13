# 2026-07-13 — curation rework: panel nav/handler wiring (ORDER 017 item 2)

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · NIGHT-RUN curation rework · mandate: ORDER 017 item 2 (curation report PR #327)

## Scope

The "panel nav/handler wiring" bundle from the night-run curation review
(`docs/review/curation-report-2026-07-13.md`): three trivial handler swaps
that retire 5 pending terminals whose live destinations already ship at
HEAD — no new surfaces, no wire-byte changes (every affected button's
label/style/custom_id stays golden-pinned verbatim; only the server-side
handler route moves).

1. `sb/domain/server_management/panels.py` — the hub's 🛡️ Moderation /
   🎭 Roles / 🧹 Cleanup buttons: `_pending(...)` terminals →
   `PanelRef("moderation.hub")` / `PanelRef("role.hub")` /
   `PanelRef("cleanup.hub")` (the Channels/Setup pattern in the same spec).
2. `sb/domain/mining/panels.py` — `mining.workshop.ws_back`:
   `mining.workshop_hub_pending` → `PanelRef("mining.hub")` (the `sk_hub`
   pattern).
3. `sb/domain/utility/panels.py` — `utility.panel.invite`:
   `utility.invite_pending` → the live argless
   `HandlerRef("utility.invite_view")` (the `!invite` command's route).

Excluded: cleanup panels (sibling rework lane) and btd6 paragon (own lane).

## What shipped

(fills at close-out)

## 💡 Session idea

(fills at close-out)

## ⟲ Previous-session review

(fills at close-out)

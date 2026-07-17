# 2026-07-17 — Port: Help Home-message builder (Q-0059)

> **Status:** `in-progress`

- **📊 Model:** [[fill: family-level model name this harness reports, at flip]]

## Scope

Port the Q-0059 Help Home-message builder, retiring the
`help.editor_home_message_pending` stub. The Help editor's "🏠 Home
message" button currently refuses with a pending stub; this slice gives it
a real builder that customizes the Help Home frame's title / body / accent
color with a mandatory preview before save, byte-faithful to the live bot.

## Plan

- Migration 0056 — add the Help home-message columns.
- HomeMessage read model in `sb/domain/help/overlay.py`.
- `help.set_home_message` write lane in `sb/domain/help/overlay_ops.py`.
- `editor_home_message` panel + 2 modals + ENUM color selector + handlers
  in `sb/domain/help/editor.py`.
- Live-wire `help.home` to consume the saved home message.
- Mint an oracle-verified golden for the new surface.

## Deviation ledger

[[fill: deviations from plan / oracle, with code anchors — at flip]]

## Close-out

[[fill: build landed — PR #, commits, CI/gate state, corpus movement — at flip]]

## 💡 Session idea

[[fill: reusable insight / guard recipe with code anchors — at flip]]

## ⟲ Previous-session review

[[fill: what the prior session's close-out saved or cost this one — at flip]]

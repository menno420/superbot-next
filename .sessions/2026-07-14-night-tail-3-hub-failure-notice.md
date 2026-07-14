# 2026-07-14 — setup: hub per-section failure notice (night-tail-3)

> **Status:** `in-progress`

- **📊 Model:** `Fable 5` · NIGHT-TAIL slice 3 · mandate: the small
  shared catch seam the SectionRecoveryView lane (#444, merged 32f72ec)
  sized as its own follow-up — claimed in
  `control/claims/night-tail-setup-mint.md` (claim PR #454).

## Scope

The #444 card's ledgered deferral (`.sessions/2026-07-13-night-recovery-
view.md`): "the oracle hub's section-failure notice (\"⚠️ Section
`slug` failed\") — the target's hub buttons dispatch straight to
per-section handlers with no shared catch seam; wiring it means either
a router-level notice hook or per-section wraps, a small own slice."

Build that slice: one shared catch seam at the sections hub's own
dispatch edge, so a raising `setup.open_section_{slug}` handler
surfaces the durable "⚠️ Section `slug` failed" workspace notice (the
`push_setup_notice` lane #444 shipped) plus a click-level BLOCKED ack,
instead of today's generic kernel error envelope
(`sb/kernel/interaction/resolve.py` `from_exception`). Success paths
pass through untouched. Tests in `tests/unit/setup_band/`.

Oracle access note: the GitHub MCP oracle read documented in
`docs/CAPABILITIES.md` (2026-07-13 workaround) is DENIED in this seat —
verbatim: `Access denied: repository "menno420/superbot" is not
configured for this session. Allowed repositories:
menno420/superbot-next` (one attempt, deny-wins). The notice copy is
recovered from in-repo pins instead: the #444 card's quoted title and
the exemplar `test_notice_render_composes_the_pushed_embed`
(`tests/unit/setup_band/test_section_recovery.py:517` — title
"⚠️ Section `channels` failed", description "See logs for details.",
style red).

## Close-out

[[fill: landed seam + evidence]]

## 💡 Session idea

[[fill]]

## ⟲ Previous-session review

[[fill]]

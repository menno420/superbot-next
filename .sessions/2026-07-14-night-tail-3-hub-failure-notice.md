# 2026-07-14 — setup: hub per-section failure notice (night-tail-3)

> **Status:** `complete`

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

Landed as PR #455 (implementation commit 7d49d0e). One shared seam in
`sb/domain/setup/panels.py`: every sections-hub button now carries
`HandlerRef("setup.hub_open_section_{slug}")` — `_hub_section_dispatch`
resolves the section's own `setup.open_section_{slug}` route at click
time (`_resolve_section_open`, the recovery.py `_run_section_flow`
twin, module-level so tests can seam it) and passes success returns
through byte-untouched; any exception (including an unresolvable
route) logs, posts the durable "⚠️ Section `slug` failed" / "See logs
for details." / red workspace record through `push_setup_notice`, and
answers the click `Reply(BLOCKED, "⚠️ Opening **{label}** failed — see
logs. Nothing was applied or skipped.")` with the "A failure record
was posted to the setup workspace." tail only when the push returned
True (the notices.py caller-decides-the-fallback contract). Wire bytes
unchanged — `setup_section:{slug}` custom_ids/labels/emoji/styles
verbatim, so compat + sim-gate baselines needed no regen; the manifest
snapshot recompiled via `tools/manifest_compile.py --write` (the 10
wrapper handler refs + the hub spec's re-pointed buttons, nothing
else). Hub-origin recovery-panel mount stays deliberately unwired —
the oracle's own posture (recovery.py: "grammar the oracle carried but
never wired"); the sized slice was the notice.

Decisions flagged: the BLOCKED ack copy is target-authored (the oracle
hub's click-level copy is unrecoverable in this seat — the access
denial ledgered under Scope), composed from the repo's own "— see
logs." / "Nothing was applied or skipped." idioms; the notice bytes
themselves are the #444-pinned exemplar, not invented.

Evidence: `python3 -m pytest tests/ -q` **3043 passed, 15 skipped**
(8 new in `tests/unit/setup_band/test_hub_section_failure.py`,
DB-free per the wizard-interior convention); `manifest_compile` green
post-write; sim-gate OK (1591 [A]) · compat-frozen OK · shadowing /
namespace / no-skip / config-usage clean; `bootstrap.py check
--strict` green except this card's own designed born-red hold + 4
pre-existing claims-lane advisories (never exit-affecting).

## 💡 Session idea

The catch seam is hub-shaped only by where it's registered — the same
wrap-the-registered-route pattern would harden the wizard's Jump-to-
section select and the essential steps' advance lane, which also
dispatch to per-section/per-step handlers and today fall through to
the kernel envelope. Recipe: lift `_hub_section_dispatch` into a
`section_card.guarded_dispatch(route_name, *, record_title)` helper,
parameterize the notice title, and pin each new call site with a
test_hub_section_failure.py-style pass-through + failure pair — the
notice module needs zero changes (title/description/style are already
per-post params).

## ⟲ Previous-session review

The night-recovery-view session (PR #444) closed exactly as carded —
recovery panel + notice lane landed layer-legal with the oracle bytes
test-pinned, and its deferral paragraph is a model of sizing honesty:
it named the missing seam ("no shared catch seam"), both wiring
options, and left an in-repo copy exemplar (the notice-render test)
precise enough that this slice never needed the oracle at all — which
mattered, since the CAPABILITIES-documented MCP oracle read is denied
in this seat. One gap: the card says the hub's section-failure record
"rides" push_setup_notice in the oracle inventory section, which reads
as already-wired until the deferral paragraph 40 lines later corrects
it — deferrals belong beside the feature they qualify.

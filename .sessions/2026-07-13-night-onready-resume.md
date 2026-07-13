# 2026-07-13 — setup on-ready resume sweep + app-boot seam (ORDER 019 item 5a, night lane)

> **Status:** `complete`

- **📊 Model:** `Fable (Claude 5 family)` · NIGHT lane · mandate: ORDER 019
  item 5(a), setup row of `docs/status/completeness-table-2026-07-13.md`
  ("the on-ready resume sweep (needs an app-boot seam)"); claim:
  `control/claims/night-setup-followups-windowed-select.md` (PR #431)

## Scope

Land the app-boot seam the setup on-ready resume sweep needs, then the
sweep itself: a kernel-band boot-hook registry (registration + firing
order + per-hook error isolation) the manifest wires — no kernel→domain
import edge — plus the `sb/domain/setup` sweep porting the oracle's
`SetupCog.on_ready` pair (`_resume_launchers` +
`revive_essential_flows`, menno420/superbot @bbc524e4): on boot, find
persisted setup-session rows with workspace/essential message pointers
and re-render them in place to the correct state (vanished essential
message → clear the anchor through the audited K7
`setup.clear_essential_anchor` op, the oracle semantics).

Definition of done: seam + sweep implemented + unit-tested (seam
registration/order/isolation; sweep resumed/re-rendered vs no-op
branches), `python3 -m pytest` green, bootstrap strict check green.

## Close-out

Landed as PR #437 (implementation commit a383d3a). Three seams, all
layer-legal: `sb/kernel/lifecycle/boot_hooks.py` (register/run with
deterministic `(order, seq)` firing, idempotent per-name
re-registration for the manifest `ENSURE_REFS` re-run, per-hook
isolation — the oracle's per-guild `on_ready` try/except lifted to
per-domain); the panel engine's message-editor port +
`edit_anchored_panel` (render fresh → edit onto a PERSISTED
channel/message pair — the boot-time twin of `refresh_session_view`;
uninstalled answers `unavailable`, never a crash) with the discord
implementation `DiscordPanelMessageEditor` (fetch → edit; NotFound →
`missing`, forbidden/HTTP → `failed` — the oracle branches verbatim);
and the sweep `sb/domain/setup/resume.py` (one
`store.list_resumable_sessions` roster read replaces the oracle's
`bot.guilds` walk; leg 1 refreshes the workspace anchor and NEVER
clears pointers on a gone message, leg 2 edits the interrupted flow to
the compat-pinned `essential_setup:resume` bridge and clears the
anchor through the K7 op when the message vanished). Wiring:
`sb/manifest/setup.py` registers the hook, `sb/app/main.py` installs
the editor at step 10 and fires `run_boot_hooks()` at step 16b (gateway
RUNNING, all ports live). Evidence: 2910 passed / 15 skipped
(`python3 -m pytest tests/ -q`; 19 new across
tests/unit/kernel/test_boot_hooks.py, tests/unit/panels/
test_edit_anchored.py, tests/unit/setup_band/test_onready_resume.py);
`bootstrap.py check --strict` green minus this card's own designed
born-red hold; shadowing/namespace/no-skip/config/egress guards clean.
Decisions flagged: the sweep's launcher leg refreshes the TARGET's
persisted anchor (`setup.hub`, the depth chooser record_workspace_open
posts) because the oracle's on-guild-join launcher surface
(SetupLauncherView + status-aware label rebind) is unported in this
build — that panel stays a named successor and its labels ride this
same edit lane when it lands; the editor port installs UNGATED like
the channel emitter (an own-message edit carries no guild-mutation
class); hooks take no arguments (durable rows already know their
guilds). Deferral: the launcher-panel port itself (with on_guild_join)
— out of this item's scope, unclaimed.

## 💡 Session idea

The kernel already persists every channel-sent panel in
`panel_anchors` (sb/kernel/panels/anchors.py records; the engine skips
interaction surfaces), and this slice added the exact edit lane a
generic refresher needs — but each domain still has to hand-roll its
own boot sweep. One kernel boot hook registered by the composition
root ("panels.refresh_anchors": read non-stale `panel_anchors` rows →
`edit_anchored_panel` each → mark `is_stale` on `EDIT_MISSING`) would
give every future anchored panel restart-refresh for free and retire
the per-domain sweep class at its second consumer. Guard recipe:
extend `sb/kernel/panels/anchors.py` with a `list_active_anchors` +
`mark_stale` pair, hook them to `edit_anchored_panel`
(sb/kernel/panels/engine.py), pin with a boot_hooks-style unit test
that a missing message flips `is_stale` and never blocks the next row.

## ⟲ Previous-session review

The setup-compound-2 session (PR #429) closed its lane exactly as
carded — routing resolver port + `routing.set_policy` +
`automation.add_rule` landed with the full resolver-precedence matrix
pinned and the CI-red `check_compat_frozen` amendment routed through
the sanctioned `--write` path, not a hand edit — and its harness note
(widen FakeConn, run the real K7 engine) held up as the lane's
reusable trail; the one gap worth naming is that its own completeness
row still lists "the automation-rule apply seam" as a surviving
follow-up in the setup row (the clause its PR retired), the same
stale-row class this session's table true-up just cleaned for the
resume sweep.

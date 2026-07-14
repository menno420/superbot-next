# 2026-07-14 — setup on-guild-join launcher panel port (night-tail-2)

> **Status:** `complete`

- **📊 Model:** `Fable 5` · NIGHT-TAIL lane · mandate: night-tail-2 slice
  (claim `control/claims/night-tail-setup-mint.md`, PR #454) — port the
  oracle's on-guild-join setup launcher (menno420/superbot @bbc524e4:
  `disbot/cogs/setup_cog.py` `on_guild_join`/`_handle_join` +
  `disbot/views/setup/launcher.py` `SetupLauncherView`/`post_launcher`/
  `pick_launcher_channel`) into `sb/domain/setup`, riding the #437
  anchored-panel seam family.

## Scope

Arm an `on_guild_join` gateway feed the idiomatic way (adapter listener →
kernel consumer registry, the reaction-feed shape), add the panel engine's
message-POSTER port (the `edit_anchored_panel` twin for headless channel
posts), port the launcher panel (oracle copy verbatim: title, description,
footer, the 7 static-custom-id buttons, the status-aware Start label set)
and the join handler (private `#superbot-setup` first with the owner-ping
content, `pick_launcher_channel` fallback ladder, no-double-post guard,
session upsert with the minted pointers through the K7
`setup.start_session` op). Update the stale `resume.py` "NOT ported"
comment. Tests in `tests/unit/setup_band/` + `tests/unit/panels/`.

Definition of done: feed + panel + handler + persistence landed,
`python3 -m pytest tests/ -q` green, `bootstrap.py check --strict` green
(minus this card's own born-red hold), PR open on `claude/night-tail-2`.

## Close-out

Landed on PR #456 (branch `claude/night-tail-2`, implementation commit
3ecf182). Four seams, all layer-legal:
`sb/kernel/interaction/guild_events.py` (the guild-join consumer
registry — the reactions.py mirror: register-at-manifest-import,
dispatch never raises, per-consumer fault isolation);
`sb/adapters/discord/guild_feed.py` (`arm_guild_join_feed` — additive
`bot.add_listener`, duck-typed guild payload incl. `system_channel_id`,
the never-raise reaction_feed posture); the panel engine's
message-POSTER port + `post_anchored_panel`
(sb/kernel/panels/engine.py — render fresh → POST into a channel with
no live interaction, the #437 `edit_anchored_panel` twin; uninstalled
answers None) with the discord implementation
`DiscordPanelMessagePoster` (sb/adapters/discord/panel_view.py —
get/fetch channel → send; the owner-mention allowlist computed through
the egress `allowed_mentions_for` seam, default-deny standing); and the
domain port `sb/domain/setup/launcher.py` (oracle copy verbatim —
launcher embed/footer/status accents, `_START_LABELS_BY_STATUS`, the
seven static `setup:*` custom ids; the join ladder: workspace-first
with the owner-ping content line on a fresh create, the no-double-post
guard on a kept anchor, then the `pick_launcher_channel` keyword ladder
over the channel-directory port; session upsert always rides the K7
`setup.start_session` op — its record leg now carries optional pointer
params, the oracle's one service function shape — and Dismiss rides the
new K7 `setup.mark_dismissed` op, audit verb `setup.session.dismissed`,
the shipped vocabulary). Wiring: the manifest declares the panel +
registers the consumer + re-arms via ENSURE_REFS; `sb/app/main.py`
installs the poster at step 10 and arms the feed at 14d; the launcher's
oracle-seeded layout is exempt-pinned through the sim-gate overlay
(manifest/layout/setup.lock.json + `check_sim_gate --write-baseline`);
resume.py's stale "NOT ported" ledger bullet rewritten. Evidence: 3070
passed / 15 skipped (`python3 -m pytest tests/ -q`); `bootstrap.py
check --strict` green minus this card's designed born-red hold; 35 new
tests (tests/unit/setup_band/test_guild_join_launcher.py + tests/unit/
panels/test_post_anchored.py); egress/namespace/shadowing/no-skip/
config guards clean. Decisions flagged in the module ledger: owner-DM
fallback unported (no DM egress port exists — honest deferral), Run
Readiness Scan answers the ported check-my-setup read (the oracle
scorecard embed fold is a diagnostic-band follow-up), View Summary
keeps the oracle's not-complete refusal + an honest terminal on the
complete branch, the resume sweep keeps rendering `setup.hub` at the
shared pointer pair (the launcher's own status-aware boot refresh is
the flagged follow-up below).

## 💡 Session idea

`handle_guild_join` and `setup.launcher_repost` both walk the same
post-ladder + `start_session` refresh, and the oracle's
`_resume_launchers` is the SAME render this build routes to `setup.hub`
— the setup row now has three surfaces sharing one "where does the
launcher live" decision but only the join path records HOW the spot was
chosen. Persisting the landing class (`workspace` / `fallback:<why>` /
`none`) as a session column would let the resume sweep re-render the
RIGHT panel per row (launcher vs hub) instead of the current
one-size-fits-hub, closing the flagged follow-up without guessing.
Guard recipe: add `launcher_surface TEXT` to `setup_session` (migration
+ `store.upsert_session`), stamp it in
`sb/domain/setup/launcher.py::_record_join_session`, branch
`resume.py::_resume_one_launcher` on it, pin with a
test_onready_resume.py case that a `workspace` row edits
`setup.launcher` and a legacy NULL row keeps `setup.hub`.

## ⟲ Previous-session review

The night-onready-resume session (PR #437) closed exactly as carded —
boot-hook seam, editor port and sweep all landed where its close-out
says, and its "Deferral: the launcher-panel port itself (with
on_guild_join) — out of this item's scope, unclaimed" line is precisely
the claim this session picks up; its module-docstring ledger in
resume.py (the "NOT ported in this build" bullet) was accurate enough
to serve as this slice's starting spec, the one friction being that the
card's guard recipe (the generic panel_anchors refresher) still sits
unclaimed while a second per-domain sweep consumer now exists — the
retire-at-second-consumer trigger it named has arrived.

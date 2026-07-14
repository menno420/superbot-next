# 2026-07-14 — setup on-guild-join launcher panel port (night-tail-2)

> **Status:** `in-progress`

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

_(in progress — written at session close with the real evidence tails.)_

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

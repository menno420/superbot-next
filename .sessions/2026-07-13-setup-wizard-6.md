# 2026-07-13 — setup wizard successors slice 6: the roles-family section flows

> **Status:** in-progress

- **📊 Model:** Fable · setup-wizard successor lane, slice 6

## Scope

Port the two ROLES-FAMILY section flows from the LOCAL oracle clone
(menno420/superbot) onto the slice-4 spine
(`sb/domain/setup/section_card.py` + `wizard_nav.py`):
`views/setup/sections/roles.py` (the time/XP auto-role tier detail —
pick a role, enter days / an XP level, each submission staging one
`set_role_threshold` row, newly registered onto the audited K7
`role.set_threshold` op; the full-row-upsert leg forces the
essential-steps fold — time + XP for the SAME role merge into ONE
staged row) and `views/setup/sections/role_templates.py` +
`services/setup_role_templates.py` (the six-template permission-free
role-bundle catalogue verbatim — community hierarchy / moderation
team / gaming / time progression / XP progression / support server —
pick → preview against the guild's roles → stage one
`create_managed_role` row per missing role; the op kind stages
FAIL-CLOSED, the logging_presets `create_channel` precedent — no
role-create K7 compound op exists). Flips `setup.open_section_roles`
/ `_role_templates` into `wizard.py`'s `_LIVE_SECTIONS`;
`cog_routing` · `ticket` stay honest terminals (slice 7 closes the
lane). Copy/labels/flow verbatim; the adaptation idiom is the
slice-4/5 doctrine (renderer overrides composing the embed, flow
state per guild:user, provenance-labelled K9 rows, G-10 modals for
the number entries — a native role pick cannot open a modal here, so
the pick reveals a declared modal button, ledgered).

## 💡 Session idea

`role_templates` and `roles` now stage rows that AGREE on a role's
tier from two directions (a template's `time_days`/`xp_level` spec
vs a hand-set `set_role_threshold` for the same role) but under
DIFFERENT op kinds and slot keys — the draft can carry both without
conflict, and apply order decides silently. A cross-section slot
reconciler (or at least a Final-Review warning when a
`create_managed_role` row's tier spec overlaps a staged
`set_role_threshold` for the same role name) would surface the
collision the oracle never had to think about, because its
dispatcher applied template tiers through the same threshold seam.

## ⟲ Previous-session review

(slice 5, the settings-write flows)

The slice-5 notes were load-bearing and accurate — the
`role.set_threshold` full-row-upsert warning saved this slice from
staging time/XP rows that would clobber each other at apply, and
the `_short_label` stored-label blindness note turned into two new
branches instead of a debugging session. One gap: the card said
"three sections registered without touching section_card.py at all"
but stayed silent on `sections.py` op_kinds accuracy — `roles`
op_kinds=`("set_role_threshold",)` and `role_templates`
op_kinds=`("create_managed_role",)` were declared back in slice 4
and turned out to reconcile against the oracle sources exactly.

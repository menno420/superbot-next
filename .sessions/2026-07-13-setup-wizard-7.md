# 2026-07-13 — setup wizard successors slice 7 (FINAL): cog_routing + ticket + lane closure

> **Status:** complete

- **📊 Model:** Fable · setup-wizard successor lane, slice 7 (closes the lane)

## Scope

Port the last two section flows from the LOCAL oracle clone
(menno420/superbot) onto the slice-4 spine and CLOSE the
setup-wizard-successors lane: `views/setup/sections/cog_routing.py` +
`services/cog_routing_profiles.py` (the scope → target → cog →
Enable/Disable walker plus the four named routing profiles, each pick
staging one `set_cog_routing` row — the op kind stages FAIL-CLOSED,
the logging_presets `create_channel` precedent: the compiled
architecture carries NO live command-routing resolver, its own
`access_projection.py` axis-3 ledger says so) and
`views/setup/sections/ticket.py` (the thin wizard adapter onto the
ALREADY-SHIPPED `ticket.setup` panel — the oracle section stages NO
draft op; all writes ride the audited `ticket.update_config` /
`ticket.create_log_channel` K7 lanes, `sections.py` op_kinds=() agrees
with the oracle source). Flips `setup.open_section_cog_routing` /
`_ticket` into `wizard.py`'s `_LIVE_SECTIONS` — all 10 sections walk
their full flow. Lane closure: the wizard.py docstring's
named-successors paragraph flips to none-remaining, the completeness
table's setup row records the finished truth + the surviving
follow-ups, and `control/claims/setup-wizard-successors.md` closes by
deletion (the PR #404 settings-admin convention).

## 💡 Session idea

The cog-routing cog picker re-meets the oracle's #1040 bug class from
the other side: the oracle fixed its 25-option truncation with a
`PaginatedSelectView`, but the grammar's ENUM select still clamps at
25 — so the 43-row subsystem harvest renders its first 25
alphabetically and silently drops `moderation`/`role`/`settings`/`xp`,
EXACTLY the cogs the oracle's fix docstring names. The access_map
first-25 window precedent ledgers it, but this is now the second
surface waiting on the same windowed-select grammar successor — worth
promoting that successor from "named lane" to a scheduled slice, since
each new >25-option surface silently re-ships the bug the oracle
already fixed once.

## ⟲ Previous-session review

(slice 6, the roles-family flows)

The slice-6 notes were precise where it mattered — the "reconcile
sections.py op_kinds against the oracle before trusting either" warning
checked out exactly (oracle ticket declares `op_kinds=frozenset()` and
direct-applies through the ticket panel; cog_routing declares
`{"set_cog_routing"}` and stages), and the "look for a K7 seam before
choosing fail-closed" step ended honestly at
`access_projection.py`'s own "cog routing NOT PORTED" ledger — the one
gap is that the notes pointed at `sb/domain/ticket/setup_panel.py`
without naming its panel id (`ticket.setup`), a two-minute re-derive.

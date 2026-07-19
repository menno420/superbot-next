# 2026-07-19 — D3 access-audit M1 slice 2: per-channel role-set editor panel

> **Status:** `complete`

- **📊 Model:** opus · high · feature build

## Scope

Execute **slice 2 of D3 access-audit M1** (`docs/decisions.md` D-0095; plan
`docs/design/D3-access-audit-model.md`). Slice 1 (#586, merged) landed the
durable model + write lane: migration 0057 `guild_command_access_channel_roles`,
the `SET_CHANNEL_ROLES` op, the `set_channel_roles(ctx, *, channel_id,
role_ids, allow_empty=False)` wrapper, and the `_fetch_snapshot` fold that now
populates `channel_role_sets` as `{channel_id: frozenset(role_id, …)}`. That
capacity is persisted + enforced (K6 resolver `role_not_held` gate) but had NO
UI to write it. This slice adds the UI.

Deliverables (on `settings.command_access` only — no group_edit involvement):
- A **"Role gates" FieldsBlock field** on the command_access panel rendering the
  snapshot's per-channel role-sets (channel → roles).
- A **role-set editor control** — run-minted custom_id `ca_channel_roles` — plus
  a `settings.ca_channel_roles` handler that calls Slice 1's `set_channel_roles`
  lane; refresh re-reads the snapshot (mirrors `_refresh_command_access`).

Stacked from Slice 1's branch; rebased `--onto origin/main` after #586 squash-
merged (Slice 1 SHA `64973d4b185163766e633838c7f067ec785264ae`) — the PR shows
a clean panel-only diff.

## ⚑ Flagged decision (decide-and-flag)

**Editor UX shape — a current-channel-bound RoleSelect, not a channel-then-roles
two-step.** The store write `set_channel_roles` is two-dimensional (it needs a
channel_id AND a role set in one call), but the command_access panel is
deliberately stateless ("the DB snapshot IS the panel state" — no session
dict). A true channel-then-roles two-step would need a second selector plus a
per-message session dict to carry the picked channel between two independent
interactions, contradicting that model. So the RoleSelect binds its target to
the **ambient channel** (`req.channel_id` — the channel the panel is used in);
the operator sets THIS channel's gate, and every configured channel's gate stays
visible in the Role-gates field. To edit another channel's gate you open the
panel there. This is a reversible layout call (Slice 3 could add a target-channel
picker + session state if telemetry wants cross-channel editing from one place).
It is **not** a product-semantics call: how role gates compose with the allowlist
is already fixed in the K6 resolver (`role_not_held` is an independent gate,
untouched here), so nothing was routed to the question-router.

## Result

Landed the role-gate editor on PR #587 (base `main`). The `settings.command_access`
panel grew a **"Role gates (N)" field** (`_format_role_gates` — sorted
`<#channel> — <@&role> …` lines, cleared sets render `*(cleared)*`, same 950-char
truncation guard as the allowlist field) and a **native RoleSelect
`ca_channel_roles`** (min 0 / max 25, admin-tier, run-minted) wired to
`settings.ca_channel_roles`, which writes `platform.set_channel_roles` for
`req.channel_id`, refreshes in place, and confirms (the `ca_channels` posture;
blank selection clears the gate via `allow_empty`). Files: `sb/domain/settings/
panels.py` (+field/helper/selector/row), `sb/domain/settings/handlers.py`
(+handler), `manifest.snapshot.json` (recompiled `--write`, +25 lines: the new
selector + handler ref), `manifest/layout/settings.lock.json` +
`sim/sim-gate-baseline.json` (the layout-reshape overlay + baseline, amended
with an explicit Exempt), `tests/unit/settings_band/
test_settings_hub_command_access.py`.

Verification (verbatim): the panel file →
`25 passed`; `tests/unit/settings_band/ tests/unit/band5/ tests/unit/band6/
--ignore=examples` → `1045 passed`; full `tests/unit --ignore=examples` →
`3554 passed, 15 skipped`. `check_compat_frozen: OK` (the
`settings_command_access.*` leaves stay excluded from the freeze — no pin
drift). `manifest_compile: green`. `check_sim_gate: OK` after amending the
lock overlay to the new 4-row layout + `--write-baseline` (the first D3 surface
to cross `PANEL_FLOOR` for a reshape, exactly as Slice 1's card foretold).
`check_symbol_shadowing` / `check_namespace` / `check_no_skip` /
`check_config_usage` clean. No Postgres needed — the panel tests monkeypatch the
snapshot read + write lanes (B2/B3 render/dispatch posture, no oracle-replay
golden: net-new rebuild surface). Did NOT merge.

## 💡 Session idea

The pinnable judgement: **when a stateless surface must drive a write whose key
is higher-dimensional than any one native control can carry, bind the surplus
dimension(s) to ambient context, not to new session state.** The role-gate write
is `(channel, roles)`; Discord's RoleSelect carries only `roles`. The instinct
is to add a channel-picker + a session dict to remember the pick across the two
interactions — but that imports statefulness into a surface whose whole
correctness story is "the DB snapshot IS the state, so a refresh is always
truthful." Binding `channel` to `req.channel_id` (ambient) keeps the write
single-interaction and the panel stateless, at the cost of per-invocation channel
scope. The general form: a native component is a projection of the write key onto
one axis; the missing axes should first be sought in *ambient interaction
context* (channel, guild, actor) before reaching for session memory — session
state is the last resort, not the default, because it is the thing a stateless
surface's invariants are paying to avoid. This is the read-side twin of Slice 1's
💡 (there: a DELETE predicate's scope must match the write's natural key; here:
an editor's key must be assembled from the cheapest available axes).

## ⟲ Previous-session review

Slice 1 (#586, store + lane) shipped `set_channel_roles` with a per-`(guild,
channel)` DELETE scope and left a precise forward note — that the Slice-2 editor
would be the first D3 surface across `PANEL_FLOOR` and need an explicit
sim/Exempt record; that prediction landed exactly (the one-row layout reshape
tripped `check_sim_gate`, resolved by amending the `settings.lock.json` overlay +
regenning the baseline), and its `allow_empty`/wrapper signature dropped straight
into the handler with zero friction — a clean, well-ledgered handoff.

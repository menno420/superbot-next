# Game sections — per-guild minigame/casino enablement (D-0082)

> **Status:** `plan`
>
> ORDER 017 item 4 design. Decision: [D-0082](../decisions.md). The SBW
> inventory+spec was requested (outbox SIM-REQUEST 2026-07-13T00:55Z,
> PR #325) and has NOT arrived — this design is spec-independent with a
> documented plug-in slot (§7). Built in 3 slices (§8).

## 1. Problem

The minigame/casino surfaces (blackjack, casino, mining, fishing, …) are
individually shipped subsystems reached through one games hub. Owners want
them consolidated into **sections** with per-guild enablement — enable a
whole section OR pick a few games — and panels that reflect the enabled
set. The SBW-side inventory+consolidation spec is requested but pending;
everything below stands on the superbot-next side alone and names the one
point the spec replaces when it lands.

## 2. Section model — a spec leaf + a registry

A frozen, stdlib-only `GameSectionSpec` dataclass in **`sb/spec/sections.py`**
(spec-leaf layer rule, `sb/__init__.py`: spec imports nothing above spec):

- section key (`str`), title (`str`), emoji (`str`)
- `games`: ordered tuple of `GameEntry(key, label, emoji, hub: PanelRef)` —
  the game key IS the owning subsystem key (`sb.spec.refs.PanelRef` is a
  spec→spec import, allowed).

The same leaf carries a small registry — `register_section` /
`get_section` / `all_sections` — collision-fenced and idempotent exactly
like `sb/kernel/panels/registry.py::register_panel` (identical re-register
is a no-op; a differing spec under the same key raises).

Sections are **declared** in `sb/manifest/games.py` (pure declarations,
manifest layer) and registered at boot alongside the games manifest.

## 3. DEFAULT inventory (honest, replaceable)

Derived from the shipped games-hub roster at HEAD `291361d`
(`sb/domain/games/panels.py:104-131`, `GAMES_COMPETITIVE` /
`GAMES_ACTIVITIES` — the hub already renders these two groups):

- `competitive` 🏆 — blackjack 🃏 · casino 🎰 · deathmatch ⚔️ ·
  rps_tournament ✂️
- `activities` 🎲 — mining ⛏️ · fishing 🎣 · creature 🐾 · farm 🐔 ·
  counting 🔢 · chain 🔗

This constant is derived from the ported games at HEAD and is **the SBW
replacement point** (§7) — not a product decision this design defends.

## 4. Enablement backend — REUSE governance visibility, build nothing

Per-guild enablement rides the existing governance `subsystem_visibility`
store and K7 `SET_VISIBILITY` op:

- write: `sb/domain/governance/service.py:68 set_subsystem_visibility`
  (K7-run + post-commit guild-cache invalidation)
- read: `sb/domain/governance/service.py:243 subsystem_enabled`
- enforcement ALREADY exists: every command dispatch is visibility-gated
  per guild (`sb/kernel/interaction/resolve.py:310-314`, via the installed
  `_visibility_reader` port filled by `install_authority_ports`,
  `service.py:285-300`).

No new store, no new migration, one source of truth. **Enable-all** = one
`set_subsystem_visibility` call per game in the section (clear = enabled;
`enabled=None` deletes the override back to registry default).
**Pick-a-few** = per-game rows. Disabling a game via sections and via the
governance explorer are the SAME row — no drift possible.

Read seam: **`sb/domain/games/sections.py`** exposes
`enabled_games(guild_id) -> tuple[GameSectionView, ...]` (sections with
disabled games filtered out) by calling `subsystem_enabled` per game key.
**Flag (PL-001):** this is a direct lazy domain→governance import — the
established seam shape (`sb/domain/platform/guild_teardown.py:78` imports
`governance.service` the same way; community→xp/karma, ai→settings) — so
no new port is minted; if a port is later preferred, the resolve.py
`install_visibility_reader` pattern is the template.

## 5. Settings surface (slice b)

Add a `("games", "Games", "🎮", "Competitive games and channel activities")`
group to the settings-hub roster (`sb/domain/settings/panels.py:119
_HUB_GROUPS`) and route it in `settings.open_group`
(`sb/domain/settings/handlers.py:67-90`) to a REAL games-sections panel
(today unhandled groups hit the honest pending terminal). The panel
follows the operator-spine hub pattern (`sb/domain/operator_spine.py`):

- per section: an **"Enable all"** action (writes `enabled=None` per game —
  back to default-enabled) and a **multi-select** (ENUM options = the
  section's games, selected = currently enabled) whose submit diffs the
  selection into per-game `set_subsystem_visibility` writes.
- all writes go through the K7 op with the actor's WorkflowContext — the
  audited seam, never a direct store write.

## 6. Panel update contract (slice c)

The panel engine has NO pub/sub. Updates ride the three real mechanisms:

1. **Click-time re-resolution** — every nav click re-resolves through the
   registry and re-renders fresh (`sb/kernel/panels/engine.py:382
   handle_nav`, "parents are rebuilt fresh, never captured").
2. **`refresh_session_view`** (`engine.py:340`) for live session views.
3. **Anchors** (`sb/kernel/panels/anchors.py`, `panel_anchors` migration
   0025) for channel-sent panels — currently record-only
   (`record_anchor`); no refresh sweep exists yet.

Contract: the games hub body becomes **provider-driven over
`enabled_games(guild_id)`** — the `games.hub_fields` provider
(`sb/domain/games/panels.py:140-147`) filters through the read seam instead
of the raw constants, so ANY fresh render (hub open, nav click, refresh)
reflects the enabled set. Live anchored hubs: governance post-commit cache
invalidation already fires (`service.py:64`); where an anchor row exists
and refresh is cheap, refresh it — otherwise the contract is documented
**next-interaction consistency** (the anchor store is record-only today,
so slice c ships next-interaction consistency and flags the sweep as a
named successor). Disabled games drop off the hub select; their direct
commands are ALREADY denied by resolve.py governance gating (§4).

## 7. SBW integration slot

The DEFAULT sections constant in `sb/manifest/games.py` is the **single
replacement point**. Expected SBW spec shape (mirroring the SIM-REQUEST
fields): inventory (game keys + labels), section grouping,
enable-all-or-pick-a-few semantics, panel update contract. Arrival =
replace the constant (+ extend `GameSectionSpec` if the spec adds fields);
no engine changes, no store changes.

## 8. Slice plan

| Slice | Branch | Content |
|---|---|---|
| a | `claude/minigame-sections-1` | `sb/spec/sections.py` leaf + registry, manifest declaration, `sb/domain/games/sections.py` read seam + drift-guard test (sections ↔ hub roster) |
| b | `claude/minigame-sections-2` | settings-hub `games` group + games-sections panel, K7 writes |
| c | `claude/minigame-sections-3` | games hub provider-driven over `enabled_games` |

One PR each: claim + born-red card + tests + gates. Golden-parity only
where shipped surfaces are ported (the hub bytes); new-surface behavior
(sections panel, filtering) = unit tests.

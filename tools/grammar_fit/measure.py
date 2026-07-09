#!/usr/bin/env python3
"""The cumulative rebuild-side V-2 UNITS ledger (band 1 opens it).

Method: docs/planning/grammar-spike-classification-procedure.md — the
spike's `Unit` shape with a single `tier` column, classified against the
grammar AS FROZEN in this repo at each band's base SHA. Append per band,
never rewrite (revisions need a ledger note). `python3
tools/grammar_fit/measure.py` prints the fit and regenerates RESULTS.md
next to this file. Retires at cutover per A-19 (check_escape_hatches is
the mechanical successor).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Unit:
    band: int
    subsystem: str
    kind: str           # the frozen unit vocabulary (procedure doc)
    name: str
    count: int          # multiplicity (setting x7 etc.)
    tier: int           # 1 generated | 2 declared data | 3 justified code
    rationale: str      # one line: the workflow / spec family / hatch class


UNITS: tuple[Unit, ...] = (
    # ---- band 1 / settings (PR: band1-settings; base 1088447f) ----
    Unit(1, "settings", "command", "settings", 1, 1,
         "kernel resolve() + open-panel route (PanelRef settings.hub) — zero domain code"),
    Unit(1, "settings", "panel", "settings.hub", 1, 1,
         "generated hub read-view over the K7 declaration registry (projections family)"),
    Unit(1, "settings", "store", "settings", 1, 2,
         "StoreSpec data (NAME_STABLE, AGGREGATE) — schema derived, fences generated"),
    Unit(1, "settings", "store", "subsystem_bindings", 1, 2,
         "StoreSpec data (RENAME via BindingSpec.legacy_settings_key_aliases)"),
    Unit(1, "settings", "event", "settings.changed", 1, 2,
         "EventSpec data (shipped name verbatim, BEST_EFFORT advisory)"),
    Unit(1, "settings", "handler", "scalar/binding lane legs", 4, 3,
         "thin conn-threaded DB legs behind K7 CompoundOpSpecs — domain seam by design"),
    Unit(1, "settings", "provider", "settings.hub_index", 1, 3,
         "registered read-model provider (hub index) — thin, justified"),
    Unit(1, "settings", "engine", "settings.store", 1, 3,
         "sole-writer EngineRef marker for the two tables — physical authority, by design"),
    # --- band 2 slice 1 (moderation + logging), appended 2026-07-08 -------
    Unit(2, "moderation", "command", "modmenu/moderation/warn/timeout/kick/ban/unban/clearwarnings/warnings/modlogs", 10, 1,
         "CommandSpec verbatim; group field minted for K1 parent_group"),
    Unit(2, "moderation", "op", "warn/timeout/kick/ban/unban/clearwarnings", 6, 1,
         "CompoundOpSpec DB+EFFECT legs fit; reversibility rollup honest"),
    Unit(2, "moderation", "store", "mod_logs/warnings", 2, 2,
         "StoreSpec NAME_STABLE + MEMBER_ID erasure refs"),
    Unit(2, "moderation", "event", "moderation.action_taken", 1, 2,
         "EventSpec BEST_EFFORT; payload schema declared"),
    Unit(2, "moderation", "panel", "moderation.hub", 1, 2,
         "read-view hub over provider block"),
    Unit(2, "moderation", "port", "GuildModerationActions", 1, 3,
         "domain-minted Discord state-mutation port (RC-21 sibling)"),
    Unit(2, "logging", "command", "logging (+7 group subcommands)", 8, 1,
         "CommandSpec.group carries the shipped prefix group"),
    Unit(2, "logging", "setting", "12 scalar keys + 6 channel bindings", 18, 1,
         "SettingSpec/BindingSpec slices verbatim from keys.py"),
    Unit(2, "logging", "handler", "status/enable/disable/set/routes/test/create", 7, 2,
         "thin HandlerRef routes over the settings K7 ops"),
    Unit(2, "logging", "engine", "moderation fan-out subscriber", 1, 2,
         "bus-subscribed router through the RC-21 emitter"),

    # --- band 2 slice 2 (the operator-spine eight), appended 2026-07-08 ---
    Unit(2, "operator-eight", "command", "shipped surfaces declared verbatim (admin 7, channel 17, cleanup 7, +1 each x5)", 36, 1,
         "CommandSpec + group/aliases carry every shipped name"),
    Unit(2, "operator-eight", "setting", "automod 15 / security 9+2 / welcome 10+2 / counters 4+3 / image_mod 8 / cleanup 1", 54, 1,
         "SettingSpec/BindingSpec slices verbatim; activations declared"),
    Unit(2, "operator-eight", "panel", "9 generated hub read-views", 9, 2,
         "one shared projection factory over the declaration registry"),
    Unit(2, "operator-eight", "engine", "automod rules / raid window / age gate / templates x2", 5, 1,
         "pure decision cores, injectable clock"),
    Unit(2, "operator-eight", "op", "cleanup word add/remove", 2, 1,
         "NATURAL_KEY DB lanes"),
    Unit(2, "operator-eight", "handler", "admin kernel-truth reads + pending terminals", 9, 2,
         "manifest-registry/lifecycle re-homes; declared-not-armed refusals"),

    # --- band 3 slice 1 (economy core), appended 2026-07-08 ---------------
    Unit(3, "economy", "command", "economymenu/economy/daily/work/shop/balance/pay/setlogchannel/joblist", 9, 1,
         "CommandSpec verbatim (aliases bal/wallet/transfer/jobs; G-4 cooldowns as data)"),
    Unit(3, "economy", "op", "daily/work/pay/buy", 4, 1,
         "CompoundOpSpec NATURAL_KEY lanes; balance+ledger one txn (CRIT-9/INV-F)"),
    Unit(3, "economy", "store", "economy_balances/economy_audit_log/economy/job_progress/inventory", 5, 2,
         "StoreSpec data (RENAME aggregate + NAME_STABLE ledger; MEMBER_ID erasure refs)"),
    Unit(3, "economy", "event", "economy.balance_changed", 1, 2,
         "EventSpec BEST_EFFORT verbatim; pay emits two payload builders"),
    Unit(3, "economy", "invariant", "economy.balance_ledger_reconciliation", 1, 2,
         "InvariantSpec RECONCILIATION QUARANTINE_ONLY (Q-D13) — declared data"),
    Unit(3, "economy", "panel", "economy.hub", 1, 2,
         "read-view hub over provider block"),
    Unit(3, "economy", "data", "JOBS/SHOP_ITEMS/DAILY_TIERS/ITEM_CATALOGUE", 4, 2,
         "pure data tables verbatim; the coupled item namespace + fence"),
    Unit(3, "economy", "port", "install_level_reader/install_xp_awarder", 2, 3,
         "the band-4 XP boundary — honest waiting ports, never fabricated levels"),
    Unit(3, "economy", "engine", "reverse importers x2 + log fan-out", 3, 3,
         "S14 ledger/aggregate importer bodies + bus->RC-21 emitter subscriber"),

    # --- band 3 slice 2 (treasury + inventory), appended 2026-07-08 -------
    Unit(3, "treasury", "command", "treasury/contribute/grant (aliases bank/pool/donate/deposit/disburse/payout)", 3, 1,
         "CommandSpec.group carries the shipped prefix group; staff tier = shipped manage_guild"),
    Unit(3, "treasury", "op", "contribute/disburse", 2, 1,
         "CompoundOpSpec NATURAL_KEY; pool leg + economy ledger row one txn (RS02/Q-0071)"),
    Unit(3, "treasury", "store", "guild_treasury", 1, 2,
         "StoreSpec NAME_STABLE AGGREGATE bears_value; S14 aggregate reverse importer"),
    Unit(3, "treasury", "invariant", "treasury.pool_ledger_reconciliation", 1, 2,
         "InvariantSpec RECONCILIATION QUARANTINE_ONLY over pool x treasury:* ledger rows"),
    Unit(3, "treasury", "panel", "treasury.hub", 1, 2,
         "read-view hub over provider block"),
    Unit(3, "inventory", "command", "inventory (inv)", 1, 1,
         "CommandSpec verbatim; projection-first unified browser"),
    Unit(3, "inventory", "panel", "inventory.hub", 1, 2,
         "read-view hub over the coupled item catalogue"),
    Unit(3, "inventory", "engine", "grouping/rarity/sort pure helpers", 3, 2,
         "shipped display algebra verbatim as pure functions"),
    Unit(3, "inventory", "port", "install_extra_inventory_source", 1, 3,
         "the band-6 mining/fishing merge seam — honest waiting port"),

    # --- band 3 slice 3 (the panel-action slice), appended 2026-07-09 -----
    Unit(3, "economy", "action", "hub daily/work/shop/balance/inventory/jobs/treasury/overview", 8, 1,
         "PanelActionSpec data — shipped custom_ids pinned verbatim; kernel-generated callbacks"),
    Unit(3, "economy", "selector", "jobcenter job_select + shop item_select", 2, 1,
         "SelectorSpec over the audited economy.work/economy.buy ops; provider/static options"),
    Unit(3, "economy", "panel", "economy.jobcenter + economy.shop_panel", 2, 2,
         "declared sub-panels (the shipped _WorkSubView/_ShopSubView) — nav serialized, closures gone"),
    Unit(3, "treasury", "action", "contribute (G-10 modal) + refresh", 2, 1,
         "PanelActionSpec + ModalSpec data — the shipped one-field modal as declared form"),
    Unit(3, "inventory", "action", "hub open-category x7", 7, 1,
         "PanelActionSpec -> open-child PanelRefs over the static category population"),
    Unit(3, "inventory", "panel", "category detail panels x7", 7, 2,
         "ListBlock + declared sort/filter algebra; interactive re-sort waits on the BrowserView engine (D-0034)"),

    # --- band 4 (xp + karma + community family), appended 2026-07-09 ------
    Unit(4, "xp", "command", "xpmenu/rank/givexp/resetxp/xpconfig/xpimport", 6, 1,
         "CommandSpec verbatim; admin floor as tier data (shipped @admin_or_owner)"),
    Unit(4, "xp", "op", "award/reset/import_levels/repair_level_consistency", 4, 1,
         "CompoundOpSpec NATURAL_KEY lanes (INV-G one audited seam; reset carries §2.7 confirm)"),
    Unit(4, "xp", "store", "xp", 1, 2,
         "StoreSpec RENAME (the coins-split complement) bears_value; S14 aggregate importer"),
    Unit(4, "xp", "event", "xp.awarded/xp.level_up/xp.reset", 3, 2,
         "EventSpec BEST_EFFORT verbatim; level_up CONDITIONAL via the D-0036 None-payload skip"),
    Unit(4, "xp", "invariant", "xp.level_consistency", 1, 2,
         "InvariantSpec ROW_PREDICATE REPAIRABLE (level := level_progress(xp), deterministic)"),
    Unit(4, "xp", "panel", "xp.hub", 1, 2,
         "provider-fed hub + Give/Reset G-10 modals over the audited ops"),
    Unit(4, "xp", "engine", "chat hot path + level-up fan-out + import parse core", 3, 3,
         "cooldown+gate+rng -> K7 run; bus->RC-21 announce; announcer-format regex tables"),
    Unit(4, "xp", "port", "participation gate/role granter/history scanner + economy fills", 4, 3,
         "the D-0031 waiting ports FILLED (level reader + xp awarder); 3 new honest waits"),
    Unit(4, "karma", "command", "thanks/karma/karma add//karma", 4, 1,
         "CommandSpec verbatim (aliases rep/thank; group=karma; slash ephemeral)"),
    Unit(4, "karma", "op", "give", 1, 1,
         "CompoundOpSpec NATURAL_KEY (INV-K: credit+given+audit ONE txn; ladder in-leg)"),
    Unit(4, "karma", "store", "karma/karma_audit_log", 2, 2,
         "StoreSpec NAME_STABLE aggregate+ledger, both REVERSE_IMPORTABLE (mutation_id minted)"),
    Unit(4, "karma", "event", "karma.granted", 1, 2,
         "EventSpec BEST_EFFORT verbatim payload keys"),
    Unit(4, "karma", "invariant", "karma.points_ledger_reconciliation", 1, 2,
         "InvariantSpec RECONCILIATION QUARANTINE_ONLY (the D-0031 value posture)"),
    Unit(4, "karma", "setting", "enabled/cooldown_seconds/daily_cap/reaction_emoji", 4, 2,
         "SettingSpec data — defaults pinned == policy constants (no-drift invariant)"),
    Unit(4, "karma", "engine", "react-to-thank core", 1, 3,
         "policy fast-gate -> the SAME audited op; silent-on-block by design"),
    Unit(4, "community", "command", "community (prefix+slash)", 2, 1,
         "router-only hub, shipped posture (zero business logic)"),
    Unit(4, "community", "panel", "community.hub", 1, 2,
         "pure navigation actions (XP/Karma/Leaderboards/Spotlight)"),
    Unit(4, "leaderboard", "command", "leaderboard + 11 shipped aliases", 1, 1,
         "CommandSpec verbatim (Q-A03 legacy_duplicate routes stay callable)"),
    Unit(4, "leaderboard", "panel", "leaderboard.board", 1, 2,
         "PROVIDER-FED category selector — band-6 categories appear with zero edits"),
    Unit(4, "leaderboard", "engine", "rank provider registry (xp/coins/karma)", 3, 3,
         "the shipped PR-G registry headless; register-a-provider extension seam"),
    Unit(4, "community_spotlight", "command", "spotlight (activity)", 1, 1,
         "CommandSpec verbatim"),
    Unit(4, "community_spotlight", "panel", "community_spotlight.hub + games", 2, 2,
         "provider-fed overview + the games selector's honest band-6 empty state"),
    Unit(4, "community_spotlight", "engine", "level-up feed subscriber", 1, 3,
         "the xp.level_up -> spotlight DECLARED consumption; bounded deque verbatim"),
    # --- band 5 (governance slice) --------------------------------------------
    Unit(5, "governance", "setting", "governance settings slice", 3, 2,
         "SettingSpec x3 (governance_version + the two tier-grant role ids)"),
    Unit(5, "governance", "store", "governance stores", 5, 2,
         "StoreSpec x5 (visibility/cleanup/audit/cap-overrides/templates) + 0016"),
    Unit(5, "governance", "event", "governance.* events", 5, 2,
         "EventSpec x5, compat-frozen names (events.py: Do NOT rename after v1)"),
    Unit(5, "governance", "op", "governance K7 lanes", 4, 2,
         "CompoundOpSpec x4 — the shipped GovernanceMutationPipeline as lanes"),
    Unit(5, "governance", "engine", "scope-chain resolver + TTL override cache", 2, 3,
         "resolve_visibility/resolve_execution verbatim; the chain walk and "
         "staleness bounds are runtime semantics no grammar expresses"),
    Unit(5, "governance", "engine", "subsystem registry data + tier taxonomy", 2, 2,
         "SUBSYSTEM_META 43 rows + PermissionTier metadata = declared data"),
    Unit(5, "governance", "engine",
         "port fills (K6 override/role-binding, K8 visibility)", 3, 3,
         "install_authority_ports — the S7/S9 waiting-port bodies"),
    # --- band 5 (role slice) ---------------------------------------------------
    Unit(5, "role", "command", "role commands + aliases", 17, 1,
         "CommandSpec verbatim (roles/setrole/reactroles/temprole family)"),
    Unit(5, "role", "panel", "role.hub (7 shipped buttons, ids pinned)", 1, 2,
         "PanelSpec + custom_id_override role:create…role:exemptions"),
    Unit(5, "role", "setting", "role settings slice", 4, 2,
         "SettingSpec x4 (skip_roles + the two stack toggles + rr enable)"),
    Unit(5, "role", "store", "role stores", 8, 2,
         "StoreSpec x8 (thresholds/reaction/modes/menus/options/grants/"
         "pickup/exemptions) + 0017"),
    Unit(5, "role", "op", "role K7 lanes", 12, 2,
         "CompoundOpSpec x12 incl. the grant EFFECT+compensator pair"),
    Unit(5, "role", "task", "role:grants_expiry", 1, 2,
         "ManagedTaskSpec (A-8 consumer; shipped 5-min loop as Interval)"),
    Unit(5, "role", "engine", "time/XP planners + feasibility + apply", 4, 3,
         "compute_assignments/plan_level_role_assignments/evaluate_role/"
         "classified apply — pure decision cores verbatim"),
    Unit(5, "role", "engine", "reaction runtime + xp-port fill", 2, 3,
         "handle_reaction_add/remove modes; install_xp_ports fills the "
         "D-0031/D-0036 level-role granter"),
    # --- band 5 (platform/control + proof_channel slice) -----------------------
    Unit(5, "platform", "store", "command-access stores", 2, 2,
         "StoreSpec x2 (old 050) + 0018 — the K8 admission DB truth"),
    Unit(5, "platform", "op", "platform K7 lanes", 2, 2,
         "set_access_mode / set_access_channels"),
    Unit(5, "platform", "engine", "access reader fill + TTL cache", 1, 3,
         "install_access_policy_reader — the S9 waiting-port body"),
    Unit(5, "platform", "engine", "guild-teardown registry", 1, 3,
         "guild_lifecycle.py compiled: hook registry w/ shipped isolation"),
    Unit(5, "platform", "engine", "consistency report", 1, 3,
         "severity contract + fail-isolated collector registry verbatim"),
    Unit(5, "platform", "engine", "introspection + guild snapshot", 2, 3,
         "duck-typed pure reads verbatim; snapshot privacy tokens pinned"),
    Unit(5, "platform", "engine", "K10 claims", 3, 2,
         "platform.explain_status/explain_consistency/code_context.explain "
         "byte-identical + fact gatherers"),
    Unit(5, "proof_channel", "command", "prize commands", 5, 1,
         "CommandSpec verbatim (+prize/-prize/prizestatus/prizemenu/"
         "timedprize)"),
    Unit(5, "proof_channel", "panel", "proof_channel.hub", 1, 2,
         "the _PrizeManagerView as declared grammar (G-10 modals)"),
    Unit(5, "proof_channel", "store", "proof_channel_locks", 1, 2,
         "StoreSpec + 0018 (bug #8 durable deadlines)"),
    Unit(5, "proof_channel", "op", "proof K7 lanes", 3, 2,
         "grant (record+EFFECT w/ compensator) / end / the sweep's unlock"),
    Unit(5, "proof_channel", "task", "proof:lock_reconcile", 1, 2,
         "ManagedTaskSpec — the shipped per-lock timers + on_ready "
         "reconcile as ONE minute-granularity sweep"),

    # ---- band 6 slice 1 (games substrate + wager games) ----
    Unit(6, "games", "command", "games/world/worldcard", 3, 2,
         "CommandSpec rows (games kind=both) routing panels + a view"),
    Unit(6, "games", "panel", "games.hub + games.world", 2, 2,
         "nav-only hub + world read panel, provider-fed overview"),
    Unit(6, "games", "store", "game_state + game_xp", 2, 2,
         "SESSION checkpoint store + AGGREGATE shared track "
         "(reverse-importable, erasure bodies)"),
    Unit(6, "games", "op", "games.gc_sweep_row", 1, 2,
         "the audited GC refund lane (shipped session_gc re-homed)"),
    Unit(6, "games", "task", "games:session_gc", 1, 2,
         "ManagedTaskSpec Interval(3600) over the 24h TTL"),
    Unit(6, "games", "engine", "wager primitives + game-XP core", 2, 3,
         "conn-threaded escrow/settle-once + soft-cap award policy — "
         "justified code under the K7 legs (P0-1 semantics)"),
    Unit(6, "games", "engine", "g1 session registry/dispatcher", 1, 3,
         "the §3.4 dynamic-id seam: prefix claims + resolve() re-entry "
         "(kernel port fill, one justified module)"),
    Unit(6, "blackjack", "command", "blackjack/bjtournament/bjstart/"
         "bjstatus", 4, 2, "CommandSpec rows, shipped names verbatim"),
    Unit(6, "blackjack", "panel", "blackjack.hub", 1, 2,
         "3 actions incl. G-10 bet modal"),
    Unit(6, "blackjack", "op", "solo/PvP/tournament lanes", 10, 2,
         "K7 CompoundOpSpecs over the checkpoint store; settle table "
         "in one leg each"),
    Unit(6, "blackjack", "engine", "card/deck/dealer primitives", 1, 3,
         "pure shipped math (engine.py) — justified code by design"),
    Unit(6, "blackjack", "setting", "default_entry_fee", 1, 2,
         "SettingSpec, shipped persisted key"),
    Unit(6, "rps_tournament", "command", "rps family", 7, 2,
         "CommandSpec rows, shipped names/aliases verbatim"),
    Unit(6, "rps_tournament", "panel", "rps_tournament.hub", 1, 2,
         "move ENUM selector (values->op) + rules/settings views"),
    Unit(6, "rps_tournament", "op", "solo/PvP/tournament lanes", 7, 2,
         "K7 CompoundOpSpecs; second throw settles in the same txn"),
    Unit(6, "rps_tournament", "engine", "rules tables", 1, 2,
         "closed alias/win-condition data, shipped verbatim"),
    Unit(6, "rps_tournament", "setting", "entry fee/mode/best_of", 3, 2,
         "SettingSpec rows (in-memory shipped settings made durable)"),
)


def compute() -> dict:
    total = sum(u.count for u in UNITS)
    t12 = sum(u.count for u in UNITS if u.tier in (1, 2))
    per_band: dict[int, tuple[int, int]] = {}
    for u in UNITS:
        got, all_ = per_band.get(u.band, (0, 0))
        per_band[u.band] = (got + (u.count if u.tier in (1, 2) else 0),
                            all_ + u.count)
    return {"total_units": total, "tier12_units": t12,
            "fit": (t12 / total) if total else 0.0,
            "per_band": {b: {"tier12": g, "units": a, "fit": g / a}
                         for b, (g, a) in sorted(per_band.items())}}


def render_results() -> str:
    stats = compute()
    lines = [
        "# grammar_fit RESULTS (V-2 cumulative ledger)", "",
        f"Cumulative fit: **{stats['fit']:.2%}** tier-1/2 over "
        f"{stats['total_units']} units (spike line: 85.26% / 95 units).", "",
        "| band | subsystem | kind | unit | xN | tier | rationale |",
        "|---|---|---|---|---|---|---|",
    ]
    for u in UNITS:
        lines.append(f"| {u.band} | {u.subsystem} | {u.kind} | {u.name} | "
                     f"{u.count} | {u.tier} | {u.rationale} |")
    lines += ["", "Per band:"]
    for band, row in stats["per_band"].items():
        lines.append(f"- band {band}: {row['fit']:.2%} ({row['tier12']}/{row['units']})")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    out = Path(__file__).resolve().parent / "RESULTS.md"
    out.write_text(render_results())
    stats = compute()
    print(f"grammar_fit: {stats['fit']:.2%} tier-1/2 over "
          f"{stats['total_units']} units -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

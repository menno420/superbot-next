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

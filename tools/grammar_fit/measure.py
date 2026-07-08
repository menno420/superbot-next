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

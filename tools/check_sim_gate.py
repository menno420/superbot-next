#!/usr/bin/env python3
"""check_sim_gate — the sim-reviewed-or-exempt gate (design-spec §2.10.6 /
§6 gate 4). Built to the §5 contract at ~L992/L1029: what it diffs, the gate
semantics, the encoded thresholds.

WHAT IT DIFFS: every [A]-field assignment reachable from the registered
manifests (sim.space.arrangement_assignments — the write surface is
machine-derived from field roles) merged with the manifest/layout/*.lock.json
overlays (sim.apply — the sole machine [A]-writer). Any change relative to
the committed pin `sim/sim-gate-baseline.json` without matching provenance —
a SimRef to a real sim record whose input hash matches, or an explicit
Exempt(reason) — is red. An overlay whose value differs from the
manifest-derived value for the SAME key is also red (overlay-masks-manifest
drift, trap 30 / PR #190): overlays merge last, so a stale overlay would
otherwise hide a manifest reshape from the diff entirely. Overlay-ONLY keys
(no manifest-derived counterpart) remain legitimate.

    Diff mechanics: the spec's "diffs [A]-fields against the merge base" is
    implemented as the proven committed-pinned-baseline pattern (A-2/A-19):
    a PR that changes an [A] assignment MUST update the baseline in the same
    PR, and the baseline update itself demands provenance — equivalent
    enforcement, and CI-shape-compatible with fetch-depth-1 checkouts
    (ledgered in D-0020).

ENCODED THRESHOLDS (defined on SEMANTIC input size, invariant under
arrangement, so the gate cannot be escaped by re-partitioning its output):
  - a panel is below the floor at <= 4 declared actions + selectors
    (PRE-layout, so paging can't split its way under) — its layout
    assignments are auto-exempt ("below threshold");
  - a settings surface is below the floor at <= 6 settings PER SUBSYSTEM —
    never per group, group membership being the [A] variable under gate;
  - navigation slots are permanently exempt by design (§2.4): they are
    engine-injected outside the searchable space and never appear in the
    assignment set at all.

`--write-baseline` regenerates the pin: provenance is pulled from the
overlays (the §2.10.3 carrier); an above-floor change with no overlay
provenance REFUSES to write — that change needs a sim record or an explicit
Exempt first.

Required-check designation (sim-gate as a named gate) = OWNER repo setting.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

BASELINE = REPO_ROOT / "sim" / "sim-gate-baseline.json"
RECORDS_DIR = REPO_ROOT / "sim" / "records"

PANEL_FLOOR = 4      # declared actions + selectors, pre-layout
SETTINGS_FLOOR = 6   # settings per subsystem, never per group


# ------------------------------------------------------------------ current
def manifest_assignments() -> dict[str, Any]:
    """The raw manifest-derived [A] assignments, BEFORE the overlay merge."""
    from sim.space import arrangement_assignments, registered_manifests

    return arrangement_assignments(registered_manifests())


def current_assignments() -> dict[str, Any]:
    from sim.apply import load_all_overlays

    assignments = manifest_assignments()
    for key, entry in load_all_overlays().items():
        assignments[key] = entry.get("value")
    return assignments


def overlay_mask_problems(
    overlays: dict[str, dict[str, Any]],
    manifest_derived: dict[str, Any],
    auto_exempt: set[str],
) -> list[str]:
    """Trap-30 hardening (PR #190's role 3/2/2→3/3/1 reshape passed silently;
    ledgered in control/status.md's #190 entry as the value-comparing-checker
    follow-up): because overlays merge LAST in current_assignments(), a stale
    overlay value overwrites the manifest-derived value for the SAME key —
    both "current" and the baseline then carry the OLD value while the
    manifest ships the NEW one, and nothing reds. Red any shared key whose
    overlay value differs from the manifest-derived value. Keys that exist
    ONLY in overlays (legacy-seed Exempt rows with no manifest-derived
    counterpart, e.g. the setup WizardSectionSpec.order seeds) stay
    legitimate. Auto-exempt below-floor keys stay outside the gate's
    jurisdiction, matching every other check."""
    problems: list[str] = []
    for key, entry in sorted(overlays.items()):
        if key not in manifest_derived or key in auto_exempt:
            continue
        overlay_value = entry.get("value")
        manifest_value = manifest_derived[key]
        if overlay_value != manifest_value:
            problems.append(
                f"{key}: overlay value {overlay_value!r} masks the "
                f"manifest-derived value {manifest_value!r} — amend the "
                f"manifest/layout/*.lock.json entry to the manifest truth "
                f"(then regen the baseline) or revert the manifest reshape"
            )
    return problems


def below_floor_keys(assignments: dict[str, Any]) -> set[str]:
    """Auto-exempt keys: panel anchors <= PANEL_FLOOR declared components;
    settings-surface fields when the subsystem declares <= SETTINGS_FLOOR
    settings."""
    from sim.space import registered_manifests

    exempt: set[str] = set()
    small_panels: set[tuple[str, str]] = set()
    small_settings_subsystems: set[str] = set()
    for manifest in registered_manifests():
        subsystem = str(getattr(manifest, "key", "") or "?")
        for panel in getattr(manifest, "panels", ()) or ():
            declared = len(getattr(panel, "actions", ()) or ()) + len(
                getattr(panel, "selectors", ()) or ()
            )
            if declared <= PANEL_FLOOR:
                small_panels.add((subsystem, getattr(panel, "panel_id", "")))
        settings = getattr(manifest, "settings", ()) or ()
        if len(settings) <= SETTINGS_FLOOR:
            small_settings_subsystems.add(subsystem)

    for key in assignments:
        parts = key.split(":", 2)
        if len(parts) != 3:
            continue
        subsystem, anchor, field_token = parts
        if (subsystem, anchor) in small_panels:
            exempt.add(key)
        if subsystem in small_settings_subsystems and field_token.split("/")[-1].startswith(
            "SettingSpec."
        ):
            exempt.add(key)
    return exempt


# ----------------------------------------------------------------- baseline
def load_baseline(path: Path | None = None) -> dict[str, dict[str, Any]]:
    path = path if path is not None else BASELINE
    if not path.exists():
        return {}
    return json.loads(path.read_text()).get("assignments") or {}


def _provenance_problems(key: str, provenance: Any) -> list[str]:
    if not isinstance(provenance, dict):
        return [f"{key}: entry has no provenance (SimRef or Exempt required)"]
    if "exempt" in provenance:
        reason = provenance["exempt"]
        if not isinstance(reason, str) or not reason.strip():
            return [f"{key}: Exempt with an empty reason"]
        return []
    sim_ref = provenance.get("sim_ref")
    if not isinstance(sim_ref, dict):
        return [f"{key}: provenance is neither sim_ref nor exempt"]
    record_id = sim_ref.get("record_id", "")
    record_path = RECORDS_DIR / f"{record_id}.json"
    if not record_path.exists():
        return [f"{key}: sim_ref names missing record sim/records/{record_id}.json"]
    record = json.loads(record_path.read_text())
    recorded = (record.get("input_hashes") or {}).get("snapshot")
    if recorded != sim_ref.get("input_hash"):
        return [
            f"{key}: sim_ref input_hash {sim_ref.get('input_hash')!r} does not "
            f"match record {record_id}'s snapshot hash {recorded!r} — re-run the sim"
        ]
    return []


def check() -> list[str]:
    from sim.apply import OverlayKeyRejected, load_all_overlays

    problems: list[str] = []
    try:
        overlays = load_all_overlays()
    except OverlayKeyRejected as exc:
        return [str(exc)]

    assignments = current_assignments()
    auto_exempt = below_floor_keys(assignments)
    baseline = load_baseline()

    # every overlay entry carries valid provenance (§2.10.3)
    for key, entry in overlays.items():
        problems.extend(_provenance_problems(key, entry.get("provenance")))

    # an overlay must never mask a differing manifest-derived value (trap 30)
    problems.extend(
        overlay_mask_problems(overlays, manifest_assignments(), auto_exempt)
    )

    for key, value in assignments.items():
        if key in auto_exempt:
            continue
        pinned = baseline.get(key)
        if pinned is None:
            problems.append(
                f"{key}: [A] assignment not pinned — a new/changed arrangement "
                f"needs a sim record or an explicit Exempt "
                f"(check_sim_gate --write-baseline after providing one)"
            )
            continue
        if pinned.get("value") != value:
            problems.append(
                f"{key}: [A] assignment changed (pinned {pinned.get('value')!r} "
                f"-> {value!r}) without a baseline update"
            )
        problems.extend(_provenance_problems(key, pinned.get("provenance")))

    current_keys = set(assignments) - auto_exempt
    for stale in sorted(set(baseline) - current_keys):
        problems.append(
            f"{stale}: baseline pin has no live [A] assignment (remove it in "
            f"the same PR that removed the surface)"
        )
    return problems


def write_baseline() -> int:
    from sim.apply import load_all_overlays

    overlays = load_all_overlays()
    assignments = current_assignments()
    auto_exempt = below_floor_keys(assignments)
    baseline = load_baseline()

    # refuse to re-pin a stale overlay value over a reshaped manifest (trap 30)
    masked = overlay_mask_problems(overlays, manifest_assignments(), auto_exempt)
    if masked:
        for p in masked:
            print(f"REFUSED {p}")
        print(
            "--write-baseline refused: overlay-masks-manifest value drift — "
            "amend the lock overlay(s) to the manifest truth first"
        )
        return 1

    out: dict[str, dict[str, Any]] = {}
    refused: list[str] = []
    for key, value in sorted(assignments.items()):
        if key in auto_exempt:
            continue
        overlay_entry = overlays.get(key)
        prior = baseline.get(key)
        if overlay_entry is not None:
            provenance = overlay_entry.get("provenance")
        elif prior is not None and prior.get("value") == value:
            provenance = prior.get("provenance")
        else:
            refused.append(key)
            continue
        out[key] = {"value": value, "provenance": provenance}

    if refused:
        for key in refused:
            print(
                f"REFUSED {key}: no provenance available — run the sim and "
                f"apply its overlay (sim.apply), or write an explicit "
                f"Exempt(reason) overlay entry first"
            )
        return 1
    BASELINE.write_text(
        json.dumps({"schema_version": 1, "assignments": out}, indent=1, sort_keys=True)
        + "\n"
    )
    print(f"sim-gate-baseline.json written ({len(out)} pinned assignments)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_sim_gate")
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args(argv)
    if args.write_baseline:
        return write_baseline()
    problems = check()
    if problems:
        for p in problems:
            print(f"RED {p}")
        print(f"check_sim_gate: {len(problems)} problem(s)")
        return 1
    assignments = current_assignments()
    print(
        f"check_sim_gate: OK — {len(assignments)} [A] assignment(s), "
        f"{len(below_floor_keys(assignments))} auto-exempt below-floor"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

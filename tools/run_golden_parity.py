#!/usr/bin/env python3
"""run_golden_parity — the golden-parity gate driver (design-spec §6 gate 5).

Two legs, two jobs in .github/workflows/golden-parity.yml:

  --gate    The REQUIRED-check semantics: every `ported` subsystem in
            parity/parity.yml replays its goldens against the bot under test
            and MUST be green; `pending` subsystems are expected-red and
            REPORTED, not failing. With zero ported subsystems the gate is
            vacuously green — that is the design (the check can be marked
            required from day one without blocking the build), and the
            red-until-parity honesty lives in --report.

  --report  The full-corpus red-until-parity report: replays EVERYTHING and
            exits nonzero while anything is red. BORN RED BY DESIGN — this
            leg stays red from repo birth until the last subsystem flips
            `pending -> ported`. Red here is the expected state, not a build
            break; regressions in ported subsystems are what --gate catches.

Replay binding: the NEW bot's replay adapter (`sb/adapters/parity/` — a
fake-HTTP/gateway transport over sb/'s real interaction pipeline, bound to
the imported case model + Normalizer) satisfies the old harness's
`Harness.start()` contract. Cases come from `parity.cases.CURATED_CASES`
plus golden-document reconstruction (`sb.adapters.parity.cases`) — the old
bot is never imported here. Replay needs Postgres (DATABASE_URL — the CI
service container); without it every replay attempt reports the binding
failure and the corpus is red.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

GOLDENS_ROOT = REPO_ROOT / "parity" / "goldens"


def _load_parity_yml() -> dict:
    import yaml

    return yaml.safe_load((REPO_ROOT / "parity" / "parity.yml").read_text())


def _golden_counts() -> dict[str, int]:
    return {
        d.name: sum(1 for _ in d.glob("*.json"))
        for d in sorted(GOLDENS_ROOT.iterdir())
        if d.is_dir()
    }


def _replay_binding() -> tuple[object, str] | tuple[None, str]:
    """Try to bind the NEW bot's replay harness (boot + close probe).

    Returns (boot_module, "") on success or (None, reason). The probe
    actually attempts ``Harness.start()`` — an import alone would
    false-green (the pre-adapter lesson); a missing/unreachable Postgres is
    the expected local failure mode (CI provides the service container).
    """
    import asyncio

    try:
        from sb.adapters.parity import boot  # noqa: PLC0415 - deliberate late bind
    except Exception as exc:  # noqa: BLE001 - report, never crash the driver
        return None, f"no bot-under-test binding ({type(exc).__name__}: {exc})"

    async def _probe() -> None:
        harness = await boot.Harness.start()
        await harness.close()

    try:
        asyncio.run(_probe())
    except Exception as exc:  # noqa: BLE001 - env failure (no DB), not a golden
        return None, f"no bot-under-test binding ({type(exc).__name__}: {exc})"
    return boot, ""


async def _replay_corpus(only_subsystems: set[str] | None,
                         *, verbose_failures: int = 8):
    """Boot once, replay the (filtered) corpus, close. Returns
    (results, missing) where results is {case_id: (subsystem, ok, problems)}
    and missing counts goldens whose cases could not be reconstructed."""
    from sb.adapters.parity import boot as sb_boot
    from sb.adapters.parity.cases import load_replay_cases
    from sb.adapters.parity.runner import golden_path, replay_case

    cases = load_replay_cases(GOLDENS_ROOT)
    harness = await sb_boot.Harness.start()
    results: dict[str, tuple[str, bool, list[str]]] = {}
    try:
        for case in cases:
            subsystem = golden_path(GOLDENS_ROOT, case).parent.name
            if only_subsystems is not None and subsystem not in only_subsystems:
                continue
            try:
                ok, problems = await replay_case(harness, case, GOLDENS_ROOT)
            except Exception as exc:  # noqa: BLE001 - a crash is a red, not a halt
                ok, problems = False, [f"replay crashed: {type(exc).__name__}: {exc}"]
            results[case.id] = (subsystem, ok, problems)
    finally:
        await harness.close()
    return results


def run_gate() -> int:
    parity = _load_parity_yml()
    subsystems: dict[str, str] = parity.get("subsystems") or {}
    ported = sorted(s for s, st in subsystems.items() if st == "ported")
    pending = sorted(s for s, st in subsystems.items() if st == "pending")
    counts = _golden_counts()

    print(f"golden-parity gate: {len(ported)} ported / {len(pending)} pending")
    for name in pending:
        print(f"  PENDING (expected-red, reported not failing): {name} "
              f"[{counts.get(name, 0)} goldens]")

    if not ported:
        print("gate: vacuously GREEN — zero subsystems ported; "
              "red-until-parity is carried by the --report leg")
        return 0

    binding, reason = _replay_binding()
    if binding is None:
        print(f"gate: RED — {len(ported)} subsystem(s) are flipped `ported` "
              f"but no replay is possible: {reason}")
        return 1

    import asyncio

    results = asyncio.run(_replay_corpus(set(ported)))
    failures = 0
    for case_id, (subsystem, ok, problems) in sorted(results.items()):
        if ok:
            continue
        failures += 1
        print(f"  RED {case_id} ({subsystem}): {len(problems)} diff(s)")
        for p in problems[:8]:
            print(f"      {p}")
    if failures:
        print(f"gate: RED — {failures} regression(s) in ported subsystems")
        return 1
    print(f"gate: GREEN — all {len(results)} golden(s) across "
          f"{len(ported)} ported subsystem(s) replay clean")
    return 0


def run_report() -> int:
    parity = _load_parity_yml()
    subsystems: dict[str, str] = parity.get("subsystems") or {}
    counts = _golden_counts()
    total = sum(counts.values())
    ported = sorted(s for s, st in subsystems.items() if st == "ported")

    binding, reason = _replay_binding()
    print("=" * 72)
    print("golden-parity REPORT — RED BY DESIGN until full parity "
          "(red-until-parity, design-spec §6 gate 5)")
    print("=" * 72)
    print(f"corpus: {total} goldens across {len(counts)} subsystem dirs")
    if binding is None:
        print(f"replayable: 0/{total} — {reason}")
        print(f"ported: {len(ported)}/{len(subsystems)} subsystems")
        print()
        print("No replay binding in this environment (Postgres service "
              "required). In CI this leg replays the FULL corpus through "
              "the new-bot adapter; red is the honest parity dashboard, "
              "not a build break — the required-check semantics live in "
              "the `gate` job.")
        return 1

    import asyncio

    results = asyncio.run(_replay_corpus(None, verbose_failures=0))
    per_sub: dict[str, list[bool]] = {}
    for _case_id, (subsystem, ok, _problems) in results.items():
        per_sub.setdefault(subsystem, []).append(ok)
    green_total = sum(1 for _s, ok, _p in results.values() if ok)
    print(f"replayable: {len(results)}/{total} (goldens with a "
          f"reconstructable case + live binding)")
    print(f"green: {green_total}/{len(results)} replayed cases match their golden")
    print(f"ported: {len(ported)}/{len(subsystems)} subsystems")
    print()
    for subsystem in sorted(per_sub):
        oks = per_sub[subsystem]
        state = subsystems.get(subsystem, "?")
        print(f"  {subsystem:24s} {sum(oks):4d}/{len(oks):<4d} green [{state}]")
    if green_total < total:
        print()
        print(f"report: RED — {total - green_total} golden(s) not yet at "
              "parity (EXPECTED until the last subsystem flips ported).")
        return 1
    print("report: GREEN — full-corpus parity.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_golden_parity")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--gate", action="store_true", help="required-check leg")
    mode.add_argument("--report", action="store_true", help="red-until-parity leg")
    args = parser.parse_args(argv)
    return run_gate() if args.gate else run_report()


if __name__ == "__main__":
    sys.exit(main())

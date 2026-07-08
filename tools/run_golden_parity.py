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

Replay binding: the imported parity/harness drives the OLD bot (`disbot/`)
in-process and therefore cannot boot in this repo. The NEW bot's replay
adapter (fake-HTTP responder over sb/'s real pipeline, bound to the same
case model) is port-band work; until it exists every replay attempt reports
`no bot-under-test binding` and the corpus is red. A `ported` flip without
the adapter is impossible — the gate refuses it loudly.
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
    """Try to bind a bot-under-test replay harness.

    Returns (harness_module, "") on success or (None, reason). The imported
    harness boots the OLD bot (`disbot/`, absent here by design) and its
    module import is lazy about that — so the probe must actually attempt
    ``Harness.start()``; the new bot's replay adapter satisfies the same
    start() contract when a port band builds it.
    """
    import asyncio

    try:
        from parity.harness import boot  # noqa: PLC0415 - deliberate late bind
    except Exception as exc:  # noqa: BLE001 - report, never crash the driver
        return None, f"no bot-under-test binding ({type(exc).__name__}: {exc})"
    try:
        harness = asyncio.run(boot.Harness.start())
    except Exception as exc:  # noqa: BLE001 - the expected pre-adapter state
        return None, f"no bot-under-test binding ({type(exc).__name__}: {exc})"
    asyncio.run(harness.close())
    return boot, ""


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

    # Replay each ported subsystem's goldens; any diff is a hard failure.
    # (Executed for real once the new-bot adapter exists; the harness's
    # replay engine is parity/harness/runner.py.)
    import asyncio

    async def _replay_ported() -> int:
        from parity.harness.runner import replay_case  # noqa: PLC0415
        from parity.cases import CURATED_CASES  # noqa: PLC0415
        from parity.cases.sweep import build_sweep_cases  # noqa: PLC0415

        harness = await binding.Harness.start()
        try:
            cases = list(CURATED_CASES)
            sweep_cases, _ = build_sweep_cases(harness.bot)
            known = {c.id for c in cases}
            cases.extend(c for c in sweep_cases if c.id not in known)
            failures = 0
            for case in cases:
                subsystem = golden_subsystem(case)
                if subsystem not in ported:
                    continue
                match, problems = await replay_case(harness, case, GOLDENS_ROOT)
                if not match:
                    failures += 1
                    print(f"  RED {case.id} ({subsystem}): {len(problems)} diff(s)")
                    for p in problems[:8]:
                        print(f"      {p}")
            return failures
        finally:
            await harness.close()

    failures = asyncio.run(_replay_ported())
    if failures:
        print(f"gate: RED — {failures} regression(s) in ported subsystems")
        return 1
    print("gate: GREEN — all ported subsystems replay clean")
    return 0


def golden_subsystem(case: object) -> str:
    """Mirror of parity/harness/runner.py golden_path's directory choice."""
    from parity.harness.runner import golden_path  # noqa: PLC0415

    return golden_path(GOLDENS_ROOT, case).parent.name


def run_report() -> int:
    parity = _load_parity_yml()
    subsystems: dict[str, str] = parity.get("subsystems") or {}
    counts = _golden_counts()
    total = sum(counts.values())
    ported = sorted(s for s, st in subsystems.items() if st == "ported")

    binding, reason = _replay_binding()
    if binding is None:
        print("=" * 72)
        print("golden-parity REPORT — RED BY DESIGN (red-until-parity, "
              "design-spec §6 gate 5)")
        print("=" * 72)
        print(f"corpus: {total} goldens across {len(counts)} subsystem dirs")
        print(f"replayable: 0/{total} — {reason}")
        print(f"ported: {len(ported)}/{len(subsystems)} subsystems")
        print()
        print("This leg is EXPECTED to stay red until port bands build the "
              "new-bot replay adapter and flip subsystems pending -> ported. "
              "A red here is the honest parity dashboard, not a build break; "
              "the required-check semantics live in the `gate` job.")
        return 1

    # Full-corpus replay (post-adapter): report per-subsystem green ratios,
    # red while anything diffs.
    print("full-corpus replay not yet implemented beyond the gate leg — "
          "extend run_gate()'s replay to all subsystems when the adapter "
          "lands (labeled follow-up in parity/parity.yml provenance).")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_golden_parity")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--gate", action="store_true", help="required-check leg")
    mode.add_argument("--report", action="store_true", help="red-until-parity leg")
    args = parser.parse_args(argv)
    return run_gate() if args.gate else run_report()


if __name__ == "__main__":
    sys.exit(main())

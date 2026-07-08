"""The SB_VERIFY_BOOT side-effect-free boot profile (S14, frozen L0 spec 13
§2.2 — the T-7 fix) + the restore-verify entrypoint.

`verified := boots to readiness under SB_VERIFY_BOOT (no gateway/token,
PollSupervisor + outbox relay NOT started, test-plane forced) AND the
dry-run invariant sweep is clean` — consuming dossier 11's definition via
S12's `run_verify_import` verbatim, never re-defining "verified".

Side-effect-free BY CONSTRUCTION:
  (a) no gateway connect and no bot token — `assert_intents` approval is
      irrelevant (nothing connects); outbound sends are impossible (no
      transport is built).
  (b) boot-reconcile + outbox relay SUPPRESSED — this module simply never
      builds the PollSupervisor / relay lanes; reaching readiness is a
      preflight → boot-gate → db.init fact, and boot-reconcile is a
      POST-ready steady-state step (vocab ⑤.3), so suppressing it does not
      weaken the boots-to-ready proof.
  (c) plane-fenced — preflight REFUSES SB_VERIFY_BOOT on a non-test plane
      (sb/kernel/config/preflight; the rails compose).

Run by `.github/workflows/restore-verify.yml` against a restored snapshot:
    SB_VERIFY_BOOT=true SB_DATA_PLANE=test DATABASE_URL=<restored> \
        python3 -m sb.app.verify_boot
Exit 0 = verified; non-zero prints machine-readable stop codes.
"""

from __future__ import annotations

import asyncio
import json
import sys

__all__ = ["run_verify_boot", "main"]


async def run_verify_boot(env=None) -> dict:
    """The verify-boot sequence. Returns a machine-readable report dict:
    {"verified": bool, "stage": ..., "stop_codes": [...], ...}."""
    from sb.kernel.config import StartupError, preflight

    # 1. preflight — coerce/validate config, the 4th rail, the verify-boot
    #    plane invariant. NO gateway/intent dependency beyond preflight's own.
    try:
        cfg = preflight(env)
    except StartupError as exc:
        return {"verified": False, "stage": "preflight",
                "stop_codes": ["startup_error"],
                "detail": [str(e) for e in exc.errors]}
    if not getattr(cfg, "SB_VERIFY_BOOT", False):
        return {"verified": False, "stage": "preflight",
                "stop_codes": ["verify_boot_not_enabled"],
                "detail": ["set SB_VERIFY_BOOT=true (and SB_DATA_PLANE=test)"]}

    # 2. boot-gate leg A — recompile parity against the committed snapshot.
    from pathlib import Path

    from sb.app.boot_gate import gate_recompile
    snapshot_path = Path(__file__).resolve().parents[2] / "manifest.snapshot.json"
    committed = json.loads(snapshot_path.read_text())
    violations = gate_recompile(committed)
    if violations:
        return {"verified": False, "stage": "boot_gate",
                "stop_codes": ["recompile_parity"],
                "detail": [str(v) for v in violations]}

    # 3. db.init — pool + migration runner + verify_applied_checksums against
    #    the RESTORED database (the restorability fact).
    from sb.kernel.db import pool
    try:
        await pool.init(cfg)
    except Exception as exc:  # noqa: BLE001 — the report IS the classification
        return {"verified": False, "stage": "db_init",
                "stop_codes": ["db_init_failed"], "detail": [str(exc)]}

    try:
        # 4. readiness fact: STARTING -> RUNNING with NO supervisor, NO relay,
        #    NO gateway — nothing that could act on the world is constructed.
        from sb.kernel import lifecycle
        lifecycle.set_phase(lifecycle.Phase.STARTING)
        lifecycle.set_phase(lifecycle.Phase.RUNNING)

        # 5. the dry-run invariant sweep (dossier 11 §2.5 via S12, verbatim).
        from sb.kernel.invariants.sweep import run_verify_import
        report = await run_verify_import()
        return {"verified": report.clean, "stage": "verify_import",
                "stop_codes": list(report.stop_codes),
                "invariant_violations_by_id": dict(report.invariant_violations_by_id),
                "quarantined_rows": report.quarantined_rows}
    finally:
        await pool.close()


def main() -> int:
    report = asyncio.run(run_verify_boot())
    print(json.dumps(report, indent=2, default=str))
    return 0 if report.get("verified") else 1


if __name__ == "__main__":
    sys.exit(main())

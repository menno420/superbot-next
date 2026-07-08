"""The credential-lifecycle recovery arm (S13, frozen L0 spec 12 §2.B).

`cadence.py`  — the DETECTOR: pure `rotation_due` join (registry cadence x
                rotation-ledger `last_rotated_at`) + `arm_due_rotations`
                (arms the durable one-shot; prompts the owner for roots).
`rotation.py` — the EXECUTOR: the distinguished externally-effecting durable
                one-shot — horizon-stable once(), the RESERVED /
                ISSUED_PENDING_VERIFY / VERIFIED / FAILED phase machine,
                crash-resume via 09's reconcile_on_boot.

The grammar leaf lives at sb/spec/credentials.py; the phase ledger at
sb/kernel/db/credentials.py (migration 0007). Concrete provider / Railway /
Discord API bindings are CUT-1 ops wiring behind the installable
RotationProvider port (spec 12 §6 deferral).
"""

from sb.kernel.credentials.cadence import DueRotation, arm_due_rotations, rotation_due
from sb.kernel.credentials.rotation import (
    ROTATION_TASK,
    RotationProvider,
    install_rotation_provider,
    reset_rotation_ports_for_tests,
    rotation_key,
    run_rotation,
)

__all__ = [
    "ROTATION_TASK",
    "DueRotation",
    "RotationProvider",
    "arm_due_rotations",
    "install_rotation_provider",
    "reset_rotation_ports_for_tests",
    "rotation_due",
    "rotation_key",
    "run_rotation",
]

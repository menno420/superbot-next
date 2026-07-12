"""TEMPORARY ORDER-016 red-proof fixture — a deliberate wiring break.

This module emits an event NO manifest declares: the runtime smoke's W6
emit-site scan must turn RED on it. Reverted in the same PR; the red
path stays permanently covered by tests/unit/app/test_runtime_smoke.py.
"""

from __future__ import annotations


async def broken_emit(bus) -> None:
    await bus.emit("order016.smoke_break_fixture", probe=True)

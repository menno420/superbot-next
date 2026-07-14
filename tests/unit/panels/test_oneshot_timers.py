"""K8 one-shot timers (docs/decisions.md D-0090) — the sanctioned
real-time lane for session-panel push edits: schedule fires once after
the delay, cancel disarms (idempotently), a callback exception is
contained + logged (never loop-fatal), and loop shutdown cancels a
pending timer silently (the asyncio.run posture the domain leans on)."""

from __future__ import annotations

import asyncio

from sb.kernel.panels import timers

run = asyncio.run


def test_fires_once_after_the_delay() -> None:
    async def main():
        fired: list[int] = []

        async def cb():
            fired.append(1)

        handle = timers.schedule(0.01, cb, name="t-fire")
        assert not handle.done
        await asyncio.sleep(0.08)
        assert fired == [1]
        assert handle.done

    run(main())


def test_cancel_disarms_and_is_idempotent() -> None:
    async def main():
        fired: list[int] = []

        async def cb():
            fired.append(1)

        handle = timers.schedule(0.01, cb, name="t-cancel")
        handle.cancel()
        handle.cancel()                     # idempotent — never raises
        await asyncio.sleep(0.05)
        assert fired == []
        assert handle.done

    run(main())


def test_callback_exception_is_contained_and_logged(caplog) -> None:
    async def main():
        async def cb():
            raise RuntimeError("boom")

        handle = timers.schedule(0.0, cb, name="t-boom")
        await asyncio.sleep(0.05)
        assert handle.done                  # failed, but contained

    with caplog.at_level("ERROR", logger="sb.kernel.panels.timers"):
        run(main())                         # never propagates
    assert any("one-shot timer" in rec.message
               for rec in caplog.records)


def test_negative_delay_clamps_to_immediate() -> None:
    async def main():
        fired: list[int] = []

        async def cb():
            fired.append(1)

        timers.schedule(-5.0, cb, name="t-negative")
        await asyncio.sleep(0.05)
        assert fired == [1]

    run(main())


def test_loop_shutdown_cancels_a_pending_timer_silently() -> None:
    fired: list[int] = []

    async def main():
        async def cb():
            fired.append(1)

        return timers.schedule(30.0, cb, name="t-shutdown")

    handle = run(main())                    # asyncio.run cancels pending
    assert handle.done
    assert fired == []

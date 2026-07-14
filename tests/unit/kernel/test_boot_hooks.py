"""App-boot hook registry (sb/kernel/lifecycle/boot_hooks.py — the
ORDER-019 on-ready seam): registration idempotency, firing order,
per-hook error isolation."""

from __future__ import annotations

import asyncio

import pytest

from sb.kernel.lifecycle import boot_hooks

run = asyncio.run


@pytest.fixture(autouse=True)
def fresh_registry():
    boot_hooks.reset_boot_hooks_for_tests()
    yield
    boot_hooks.reset_boot_hooks_for_tests()


def _hook(log, name, *, raises=False):
    async def hook():
        if raises:
            raise RuntimeError(f"{name} boom")
        log.append(name)

    return hook


def test_empty_registry_runs_to_empty_results() -> None:
    assert boot_hooks.registered_boot_hooks() == ()
    assert run(boot_hooks.run_boot_hooks()) == ()


def test_non_coroutine_hook_refused_at_registration() -> None:
    with pytest.raises(TypeError):
        boot_hooks.register_boot_hook("bad.sync", lambda: None)
    with pytest.raises(TypeError):
        boot_hooks.register_boot_hook("bad.value", object())
    assert boot_hooks.registered_boot_hooks() == ()


def test_fires_in_order_then_registration_sequence() -> None:
    log: list[str] = []
    boot_hooks.register_boot_hook("c.late", _hook(log, "c"), order=200)
    boot_hooks.register_boot_hook("a.first", _hook(log, "a"))
    boot_hooks.register_boot_hook("b.second", _hook(log, "b"))
    boot_hooks.register_boot_hook("z.early", _hook(log, "z"), order=1)

    assert boot_hooks.registered_boot_hooks() == (
        "z.early", "a.first", "b.second", "c.late")
    results = run(boot_hooks.run_boot_hooks())
    assert log == ["z", "a", "b", "c"]
    assert [r.name for r in results] == ["z.early", "a.first", "b.second",
                                         "c.late"]
    assert all(r.ok for r in results)


def test_reregistration_replaces_in_place() -> None:
    # the manifest ENSURE_REFS re-run posture: same name, last callable
    # wins, the firing slot is stable.
    log: list[str] = []
    boot_hooks.register_boot_hook("x.hook", _hook(log, "old"))
    boot_hooks.register_boot_hook("y.hook", _hook(log, "y"))
    boot_hooks.register_boot_hook("x.hook", _hook(log, "new"))

    assert boot_hooks.registered_boot_hooks() == ("x.hook", "y.hook")
    run(boot_hooks.run_boot_hooks())
    assert log == ["new", "y"]


def test_raising_hook_is_isolated_and_recorded() -> None:
    log: list[str] = []
    boot_hooks.register_boot_hook("a.ok", _hook(log, "a"))
    boot_hooks.register_boot_hook("b.boom", _hook(log, "b", raises=True))
    boot_hooks.register_boot_hook("c.ok", _hook(log, "c"))

    results = run(boot_hooks.run_boot_hooks())
    # the raising hook never blocked the later one (the oracle's
    # per-guild on_ready isolation, lifted to per-domain).
    assert log == ["a", "c"]
    by_name = {r.name: r for r in results}
    assert by_name["a.ok"].ok and by_name["a.ok"].error is None
    assert by_name["c.ok"].ok
    assert not by_name["b.boom"].ok
    assert "boom" in (by_name["b.boom"].error or "")

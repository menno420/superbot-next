"""Capture + replay for the NEW bot — the golden document twin.

Produces documents in EXACTLY the imported corpus's schema
(``harness_version`` 1, ``case_id`` / ``subsystem`` / ``seed`` / ``notes`` /
``steps[{input, calls, events?}]`` / ``db_delta``), reusing the imported
harness's own Normalizer, db-snapshot engine, diff and path logic — so a
replay diff line means BEHAVIOR drift, never dialect drift.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from parity.harness.capture import Normalizer
from parity.harness.cases import GoldenCase, Step
from parity.harness.dbsnap import diff_snapshots, reset_database, snapshot
from parity.harness.runner import HARNESS_VERSION, _describe_step, _diff_docs, golden_path
from parity.harness.world import DEFAULT_PERSONAS

from sb.adapters.parity.boot import Harness

__all__ = ["capture_case", "replay_case", "golden_path"]


def _flatten_components(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for row in components:
        flat.extend(row.get("components", []))
    return flat


async def _drive(harness: Harness, step: Step, minted: list[int],
                 minted_components: dict[int, list[dict[str, Any]]]) -> str | None:
    """Mirror of parity/harness/runner._drive over the new-bot harness."""
    mentions = tuple(DEFAULT_PERSONAS[m]["id"] for m in step.mentions)
    if step.kind == "command":
        content = step.content
        if "__CHANNEL_" in content and harness.world is not None:
            for name, cid in harness.world.channels.items():
                content = content.replace(f"__CHANNEL_{name.upper()}__", f"<#{cid}>")
        await harness.send_command(content, persona=step.persona,
                                   channel=step.channel, mentions=mentions)
        return None
    if step.kind == "slash":
        await harness.invoke_slash(step.name, list(step.options),
                                   persona=step.persona, channel=step.channel)
        return None
    if step.kind == "click":
        index = step.target_message - 1
        if index < 0 or index >= len(minted):
            raise ValueError(
                f"step targets <msg:{step.target_message}> but only "
                f"{len(minted)} bot messages were minted")
        message_id = minted[index]
        custom_id = step.custom_id
        component_type = step.component_type
        if not custom_id and step.component_index >= 0:
            flat = _flatten_components(minted_components.get(message_id, []))
            if step.component_index >= len(flat):
                raise ValueError(
                    f"component_index {step.component_index} out of range "
                    f"({len(flat)} components on <msg:{step.target_message}>)")
            component = flat[step.component_index]
            custom_id = component.get("custom_id", "")
            component_type = component.get("type", component_type)
        await harness.click(message_id=message_id, custom_id=custom_id,
                            component_type=component_type,
                            values=list(step.values) if step.values is not None else None,
                            persona=step.persona, channel=step.channel)
        return custom_id
    raise ValueError(f"unknown step kind {step.kind!r}")  # pragma: no cover


async def capture_case(harness: Harness, case: GoldenCase) -> dict[str, Any]:
    """Run one case against the booted NEW bot; return its golden document."""
    if harness.world is None or harness.http is None:
        raise RuntimeError("harness not started")
    random.seed(case.seed)
    harness.world.clock.set_case_base(case.id)
    harness.reset_case_state()

    before: dict[str, Any] = {}
    pool = None
    if harness.db_ready:
        from sb.kernel.db import pool as pool_mod

        pool = pool_mod
        await reset_database(pool)
        for statement in case.fixture_sql:
            await pool.execute(statement)
        before = await snapshot(pool)

    normalizer = Normalizer(harness.world)
    minted: list[int] = []
    minted_components: dict[int, list[dict[str, Any]]] = {}
    steps_out: list[dict[str, Any]] = []
    harness.take_calls()
    harness.take_events()
    harness.http.gaps.clear()

    for step in case.steps:
        resolved_custom_id = await _drive(harness, step, minted, minted_components)
        if harness.http.gaps:
            gaps = sorted(set(harness.http.gaps))
            harness.http.gaps.clear()
            raise RuntimeError(
                f"capture integrity: transport gap(s) hit during {case.id}: "
                f"{gaps} — extend sb/adapters/parity/transport.py.")
        raw_calls = harness.take_calls()
        for call in raw_calls:
            rid = getattr(call, "response_id", None)
            if rid is not None:
                minted.append(rid)
                components = (call.payload or {}).get("components")
                if components:
                    minted_components[rid] = components
        events = harness.take_events()
        events.sort(key=lambda e: e["event"])   # same fan-out-order rule
        input_doc = _describe_step(step)
        if resolved_custom_id:
            input_doc["custom_id"] = normalizer.normalize(resolved_custom_id)
        step_doc: dict[str, Any] = {
            "input": input_doc,
            "calls": normalizer.calls(raw_calls),
        }
        if events:
            step_doc["events"] = normalizer.events(events)
        steps_out.append(step_doc)

    delta: dict[str, Any] = {}
    if pool is not None:
        after = await snapshot(pool)
        delta = normalizer.db_delta(diff_snapshots(before, after))

    return {
        "harness_version": HARNESS_VERSION,
        "case_id": case.id,
        "subsystem": case.subsystem,
        "seed": case.seed,
        "notes": case.notes,
        "steps": steps_out,
        "db_delta": delta,
    }


async def replay_case(harness: Harness, case: GoldenCase,
                      goldens_root: Path) -> tuple[bool, list[str]]:
    """Re-run a case against the NEW bot and diff against its stored golden.
    True = parity (the flip evidence); the problem list is the honest gap."""
    path = golden_path(goldens_root, case)
    if not path.exists():
        return False, [f"golden missing: {path}"]
    expected = json.loads(path.read_text())
    actual = await capture_case(harness, case)
    # flag-13 dispositions (ORDER 009 / Q-0262.3): the three owner-accepted
    # corpus-red classes are dropped from BOTH docs, symmetrically, before
    # the diff — every other byte still diffs.
    from sb.adapters.parity.dispositions import apply_dispositions

    problems = _diff_docs(apply_dispositions(expected),
                          apply_dispositions(actual))
    return (not problems), problems

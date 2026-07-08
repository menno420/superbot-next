"""The replay-case corpus for the NEW bot — old-bot-free case sourcing.

The old driver enumerated sweep cases from the LIVE old bot
(``parity/cases/sweep.build_sweep_cases(bot)`` — needs discord + disbot).
For replay against the new bot the denominator is the imported GOLDENS
themselves: every golden document carries its own input record
(kind/content/name/options/persona/channel), so a sweep case is
reconstructed losslessly from its golden. Curated multi-step cases load
from ``parity.cases.CURATED_CASES`` verbatim (importable without discord;
their click steps carry component_index, which the goldens normalize away).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from parity.harness.cases import GoldenCase, Step
from parity.harness.world import DEFAULT_PERSONAS

__all__ = ["load_replay_cases", "reconstruct_case"]

_PERSONA_BY_ID = {p["id"]: key for key, p in DEFAULT_PERSONAS.items()}
_MENTION = re.compile(r"<@!?(\d{15,20})>")


def _mentions_from(content: str) -> tuple[str, ...]:
    out: list[str] = []
    for match in _MENTION.finditer(content):
        key = _PERSONA_BY_ID.get(int(match.group(1)))
        if key is not None and key not in out:
            out.append(key)
    return tuple(out)


def _step_from_input(doc: dict) -> Step | None:
    kind = doc.get("kind")
    persona = doc.get("persona", "member")
    channel = doc.get("channel", "general")
    if kind == "command":
        content = doc.get("content", "")
        return Step(kind="command", content=content, persona=persona,
                    channel=channel, mentions=_mentions_from(content))
    if kind == "slash":
        options = tuple(dict(o) for o in doc.get("options", ()))
        return Step(kind="slash", name=doc.get("name", ""), options=options,
                    persona=persona, channel=channel)
    if kind == "click":
        custom_id = doc.get("custom_id", "")
        if not custom_id or custom_id.startswith("<"):
            return None      # normalized session id — not reconstructable
        return Step(kind="click", custom_id=custom_id,
                    target_message=int(doc.get("target_message", 0)),
                    persona=persona, channel=channel)
    return None


def reconstruct_case(golden: dict) -> GoldenCase | None:
    """A GoldenCase rebuilt from one golden document, or None when any
    step is not reconstructable (curated clicks — sourced typed instead)."""
    case_id = golden.get("case_id")
    if not case_id:
        return None
    steps: list[Step] = []
    for step_doc in golden.get("steps", ()):
        step = _step_from_input(step_doc.get("input", {}))
        if step is None:
            return None
        steps.append(step)
    if not steps:
        return None
    return GoldenCase(
        id=str(case_id),
        subsystem=str(golden.get("subsystem", "_unmapped")),
        steps=tuple(steps),
        seed=int(golden.get("seed", 42)),
        notes=str(golden.get("notes", "")),
    )


def load_replay_cases(goldens_root: Path) -> list[GoldenCase]:
    """Typed curated cases first, then golden-reconstructed cases for every
    remaining golden on disk — the full replayable denominator."""
    from parity.cases import CURATED_CASES

    cases: dict[str, GoldenCase] = {c.id: c for c in CURATED_CASES}
    for path in sorted(goldens_root.glob("*/*.json")):
        golden = json.loads(path.read_text())
        case_id = golden.get("case_id")
        if not case_id or case_id in cases:
            continue
        case = reconstruct_case(golden)
        if case is not None:
            cases[str(case_id)] = case
    return sorted(cases.values(), key=lambda c: c.id)

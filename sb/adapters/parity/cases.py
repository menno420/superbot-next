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

__all__ = ["load_replay_cases", "load_replay_cases_with_report",
           "reconstruct_case"]

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
    if kind == "modal":
        # wire-type-5 modal submit (D-0073 corpus-schema growth — the
        # D-0063 deletion clause's replay-case vocabulary): custom_id is
        # the STATIC G-10 modal_id root, fields the submitted values.
        custom_id = doc.get("custom_id", "")
        if not custom_id or custom_id.startswith("<"):
            return None      # normalized session id — not reconstructable
        fields = tuple(sorted(
            (str(k), str(v)) for k, v in (doc.get("fields") or {}).items()))
        return Step(kind="modal", custom_id=custom_id, fields=fields,
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
    """Typed curated cases first (their declared order), then
    golden-reconstructed cases path-sorted — the full replayable
    denominator IN THE CAPTURE POSTURE: the old driver ran
    ``CURATED_CASES`` before the sweep (parity/run.py ``_all_cases``), and
    process-lifetime in-memory state (the K10 conversation buffer — its
    isolation registry row was deliberately per-file, never global) rides
    across cases exactly as it did at capture time. A final id-sort here
    used to replay the curated plain-chat case (``xp.chat_award``) AFTER
    the ai sweeps, starving ``sweep.ai_forget`` of the buffer its golden
    cleared (the ✅ byte)."""
    cases, _dropped = load_replay_cases_with_report(goldens_root)
    return cases


def load_replay_cases_with_report(
    goldens_root: Path,
) -> tuple[list[GoldenCase], dict[str, int]]:
    """As :func:`load_replay_cases`, plus *dropped* — {subsystem dir name:
    count of golden files on disk whose case_id never became an
    INDEPENDENTLY-replayed case} (F-003 fix): the ORIGINAL loop silently
    `continue`d past a missing case_id, a failed :func:`reconstruct_case`,
    AND a case_id collision, so a golden file in any of those states just
    vanished from the denominator instead of failing anything —
    `tools/run_golden_parity.py --gate` counted goldens on disk
    (``_golden_counts``) and replayed cases (this loader's output) through
    two DIFFERENT code paths and never compared them, so a dropped golden
    in a ``ported`` subsystem silently shrank the gate's replayed set
    instead of redding it. This report is that comparison's other half —
    the caller asserts ``golden_count == replayed_count`` per subsystem.

    A case_id collision against a CURATED_CASES entry is EXPECTED, not a
    drop (the curated case IS that golden file's intended replay — the
    typed source, not the reconstructed one); a collision against an
    EARLIER GOLDEN FILE is a genuine drop (caught in adversarial review,
    reproduced directly: two files sharing an id silently absorbed the
    second one with no signal at all, self-contradicting the gate's own
    RED line, which reports 0 unreconstructable cases while still flagging
    a count mismatch) — that second file's own content is never
    independently verified, so it counts here."""
    from parity.cases import CURATED_CASES

    curated_ids = {c.id for c in CURATED_CASES}
    cases: dict[str, GoldenCase] = {c.id: c for c in CURATED_CASES}
    dropped: dict[str, int] = {}
    for path in sorted(goldens_root.glob("*/*.json")):
        golden = json.loads(path.read_text())
        case_id = golden.get("case_id")
        subsystem = path.parent.name
        if case_id and case_id in cases:
            if case_id not in curated_ids:
                dropped[subsystem] = dropped.get(subsystem, 0) + 1
            continue        # curated: expected; earlier file: counted above
        case = reconstruct_case(golden) if case_id else None
        if case is not None:
            cases[str(case_id)] = case
        else:
            dropped[subsystem] = dropped.get(subsystem, 0) + 1
    return list(cases.values()), dropped

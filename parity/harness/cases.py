"""The golden-case model — typed, declarative, like tests/evals' EvalCase."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

__all__ = ["Step", "GoldenCase"]


@dataclass(frozen=True)
class Step:
    """One driven input. ``kind`` selects the gateway path.

    * ``command`` — a member message (prefix commands and plain messages)
    * ``slash``   — an application-command interaction
    * ``click``   — a component interaction on a bot message minted earlier
      in this case (``target_message`` = the ``<msg:N>`` ordinal)
    * ``modal``   — a wire-type-5 modal submit (``custom_id`` = the static
      G-10 modal_id root, ``fields`` = the submitted field values;
      corpus-schema growth reviewed in the D-0073 slice PR — the D-0063
      deletion clause's replay-case vocabulary)

    ``advance_s`` (D-0043 minigame-timing corpus-schema growth): how far
    the logical clock advances when this step is driven. ``None`` keeps
    the fixed 30.0 s every existing golden was captured under, so the
    growth is additive-only; a timing case sets a sub-window value (e.g.
    ``0.5`` to click Reel before the rolled bite).
    """

    kind: Literal["command", "slash", "click", "modal"]
    content: str = ""
    name: str = ""
    options: tuple[dict[str, Any], ...] = ()
    custom_id: str = ""
    #: alternative to custom_id for session-dynamic ids: click the Nth
    #: component (flattened row-major) of the target message
    component_index: int = -1
    target_message: int = 0
    component_type: int = 2
    values: tuple[str, ...] | None = None
    #: modal steps: the submitted (field_id, value) pairs, sorted by
    #: field_id (a tuple so the dataclass stays frozen/hashable).
    fields: tuple[tuple[str, str], ...] = ()
    persona: str = "member"
    channel: str = "general"
    mentions: tuple[str, ...] = ()  # persona keys, resolved to ids at run time
    #: logical-clock advance for this step, seconds; None = the fixed 30.0
    #: (the whole existing corpus — see class docstring).
    advance_s: float | None = None


@dataclass(frozen=True)
class GoldenCase:
    """One golden scenario: fixture → steps → observed outputs + DB delta."""

    id: str
    subsystem: str
    steps: tuple[Step, ...]
    fixture_sql: tuple[str, ...] = ()
    seed: int = 42
    notes: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

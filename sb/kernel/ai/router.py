"""NL route-probe registry (K10) — the task router with the domain
keyword logic CUT OUT.

The shipped ``disbot/services/ai_task_router.py`` hardcoded BTD6 / Limbus
/ YouTube classification into one ``classify()``. Here classification is a
registry of :class:`RouteProbe`s: each domain registers a deterministic,
cheap probe at its port band (band 7 registers the BTD6 entity matcher,
the projmoon keyword probe, the video-URL probe — porting their shipped
logic INTO their bands). Probes run in ascending ``order``; the first
non-None :class:`RoutedTask` wins; no match falls back to the kernel's
``general.nl_answer``.

Shipped semantics preserved for the port workers: a probe receives the raw
text plus a :class:`RouteContext` carrying the conversation cue
(``conversation_context_domains`` — the recent-turn domain signals the NL
engine gathered) and the intake-channel hint, so the entity-less-follow-up
and strategy-intake behaviours re-home unchanged.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

__all__ = [
    "RouteContext",
    "RouteProbe",
    "RoutedTask",
    "classify",
    "clear_probes_for_tests",
    "register_probe",
    "registered_probes",
]


@dataclass(frozen=True)
class RoutedTask:
    """The routing verdict for one message (shipped shape)."""

    task: str  # registered task id
    route: str  # short string for the audit row (usually == task)
    confidence: float  # 0.0..1.0 — informational
    via_conversation_cue: bool = False


@dataclass(frozen=True)
class RouteContext:
    """Cross-message signals a probe may consult (all optional)."""

    guild_id: int | None = None
    channel_id: int | None = None
    # Domains observed in the channel's recent conversation floor (e.g.
    # {"btd6"}) — lets an entity-less follow-up ("does IT make coins…")
    # reach the domain path where carryover grounding lives.
    conversation_context_domains: frozenset[str] = frozenset()
    # The channel is a domain intake surface (e.g. btd6 strategy intake).
    intake_kinds: frozenset[str] = frozenset()
    extra: dict[str, object] = field(default_factory=dict)


#: A probe returns a RoutedTask to claim the message, or None to pass.
#: Probes MUST be deterministic and cheap (keyword/regex scans — never an
#: LLM call) and MUST NOT raise; the dispatcher treats a raising probe as
#: a pass (fail-open to the general fallback, never a dropped message).
ProbeFn = Callable[[str, RouteContext], RoutedTask | None]


@dataclass(frozen=True)
class RouteProbe:
    name: str
    owner_subsystem: str
    fn: ProbeFn
    order: int = 100  # ascending; domain probes default after kernel pre-filters


_PROBES: dict[str, RouteProbe] = {}


def register_probe(probe: RouteProbe) -> RouteProbe:
    prior = _PROBES.get(probe.name)
    if prior is not None and prior != probe:
        raise ValueError(f"route probe {probe.name!r} registered twice (differing)")
    _PROBES[probe.name] = probe
    return probe


def registered_probes() -> tuple[RouteProbe, ...]:
    return tuple(sorted(_PROBES.values(), key=lambda p: (p.order, p.name)))


def clear_probes_for_tests() -> None:
    _PROBES.clear()


_FALLBACK = RoutedTask(
    task="general.nl_answer",
    route="general.nl_answer",
    confidence=0.4,  # shipped fallback confidence
)


def classify(message_text: str, ctx: RouteContext | None = None) -> RoutedTask:
    """Return the routed task for ``message_text``: first claiming probe in
    ``order`` wins; no claim → ``general.nl_answer`` (shipped fallback)."""
    context = ctx or RouteContext()
    text = message_text or ""
    for probe in registered_probes():
        try:
            verdict = probe.fn(text, context)
        except Exception:  # noqa: BLE001 — a broken probe never drops a message
            continue
        if verdict is not None:
            return verdict
    return _FALLBACK

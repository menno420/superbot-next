"""The fuzzy adapter (spec 02 §3.7): a `CommandNotFound` raw token → K1
fuzzy match → AUTO (safe corrections re-enter `resolve()` — never a
`process_commands` re-dispatch) / SUGGEST / NONE.

The AUTO/SUGGEST thresholds are C-5's (shipped `utils/command_resolution.py`
is the K8-material central typo resolver); the corpus is K1's
`command_corpus`. AUTO-run safety derives from the manifest `effect` field
(02 §9 deferral): only `effect == "read"` targets auto-run.
"""

from __future__ import annotations

import difflib

from sb.kernel.interaction.adapters import lookup_target
from sb.kernel.interaction.request import ResolveRequest, Surface
from sb.kernel.interaction.resolve import resolve

__all__ = ["FuzzyDecision", "resolve_token", "dispatch_fuzzy"]

AUTO_CUTOFF = 0.85
SUGGEST_CUTOFF = 0.6


class FuzzyDecision:
    __slots__ = ("kind", "match", "suggestions")

    def __init__(self, kind: str, match: str | None = None,
                 suggestions: tuple[str, ...] = ()):
        self.kind = kind                 # "auto" | "suggest" | "none"
        self.match = match
        self.suggestions = suggestions


def resolve_token(token: str, corpus: frozenset[str]) -> FuzzyDecision:
    matches = difflib.get_close_matches(token, sorted(corpus), n=3,
                                        cutoff=SUGGEST_CUTOFF)
    if not matches:
        return FuzzyDecision("none")
    ratio = difflib.SequenceMatcher(None, token, matches[0]).ratio()
    if ratio >= AUTO_CUTOFF:
        return FuzzyDecision("auto", matches[0], tuple(matches))
    return FuzzyDecision("suggest", None, tuple(matches))


async def dispatch_fuzzy(token: str, corpus: frozenset[str], *,
                         template: ResolveRequest) -> object | None:
    """AUTO path: rebuild the request against the corrected target and
    re-enter resolve() (identical order — authority/validate/cooldown run).
    A mutating/external target never auto-runs. Returns the Result, or the
    FuzzyDecision for suggest/none (the surface renders the did-you-mean)."""
    decision = resolve_token(token, corpus)
    if decision.kind != "auto":
        return decision
    target = lookup_target(decision.match, template.surface)
    if target is None:
        return FuzzyDecision("none")
    if getattr(target.spec, "effect", "read") != "read":
        return FuzzyDecision("suggest", None, (decision.match,))
    req = ResolveRequest(
        surface=template.surface, target=target, actor=template.actor,
        guild_id=template.guild_id, channel_id=template.channel_id,
        args=template.args, responder=template.responder, origin=template.origin,
    )
    _ = Surface  # documentation anchor: fuzzy re-enters on the SAME surface
    return await resolve(req)

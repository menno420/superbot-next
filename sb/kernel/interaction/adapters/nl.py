"""The NET-NEW nl adapter (spec 02 §3.7) — makes AI rungs EXECUTE: turns the
rung-3 `ResolvedIntent` / rung-4 plan-step `next_command` STRING into a real
`TargetRef` + validated args and funnels through `resolve()`, so an NL
intent runs the IDENTICAL order as a slash command (authority / validate /
cooldown / audit for free — no second policy surface).

Rung 4: N intents → N ResolveRequests sharing ONE minted `orchestration_id`,
resolved SEQUENTIALLY, stop on first non-SUCCESS; the aggregate is ONE
PARTIAL carrying the completed prefix (`classify_outcome` semantics). The
K10 band supplies the ResolvedIntent/plan producers; this adapter is the
`NL_INTENT`/`NL_ORCHESTRATION` producer seam.
"""

from __future__ import annotations

from sb.kernel.interaction.adapters import lookup_target
from sb.kernel.interaction.request import NLProvenance, ResolveRequest, Surface
from sb.kernel.interaction.resolve import resolve
from sb.spec.outcomes import SUCCESS

__all__ = ["request_from_intent", "request_from_plan_step", "run_plan"]


def request_from_intent(intent: object, *, responder, origin, guild_id,
                        channel_id, actor) -> ResolveRequest | None:
    """rung 3. None => next_command resolves to no declared target
    (NOT_FOUND — the NL front-end renders the miss)."""
    target = lookup_target(str(getattr(intent, "next_command", "")), Surface.SLASH)
    if target is None:
        return None
    return ResolveRequest(
        surface=Surface.NL_INTENT, target=target,
        args=dict(getattr(intent, "args", None) or {}),
        provenance=NLProvenance(
            nl_text=str(getattr(intent, "nl_text", "")),
            intent_key=str(getattr(intent, "intent_key", "")),
            confidence=float(getattr(intent, "confidence", 0.0)),
            orchestration_id=None,
        ),
        actor=actor, guild_id=guild_id, channel_id=channel_id,
        responder=responder, origin=origin,
    )


def request_from_plan_step(step: object, *, plan_id: str, responder, origin,
                           guild_id, channel_id, actor) -> ResolveRequest | None:
    """rung 4 — one step of a plan, under the shared orchestration_id."""
    target = lookup_target(str(getattr(step, "next_command", "")), Surface.SLASH)
    if target is None:
        return None
    return ResolveRequest(
        surface=Surface.NL_ORCHESTRATION, target=target,
        args=dict(getattr(step, "args", None) or {}),
        provenance=NLProvenance(
            nl_text=str(getattr(step, "nl_text", "")),
            intent_key=str(getattr(step, "intent_key", "")),
            confidence=float(getattr(step, "confidence", 0.0)),
            orchestration_id=plan_id,
        ),
        actor=actor, guild_id=guild_id, channel_id=channel_id,
        responder=responder, origin=origin,
    )


async def run_plan(steps, *, plan_id: str, responder, origin, guild_id,
                   channel_id, actor) -> list:
    """Sequential rung-4 execution: stop on first non-SUCCESS (the default
    policy; per-plan policies are the AI band's deferral). Returns the
    per-step Result list — the completed prefix plus the failing step."""
    results = []
    for step in steps:
        req = request_from_plan_step(step, plan_id=plan_id, responder=responder,
                                     origin=origin, guild_id=guild_id,
                                     channel_id=channel_id, actor=actor)
        if req is None:
            break
        result = await resolve(req)
        results.append(result)
        if result.outcome != SUCCESS:
            break
    return results

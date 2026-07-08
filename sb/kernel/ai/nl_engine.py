"""The NL engine (K10) — the domain-agnostic core of the shipped
``AINaturalLanguageStage`` (disbot/core/runtime/ai/natural_language_stage.py),
terminating in K8's ``nl`` adapter seam.

Pipeline per inbound message (the shipped 1-6 flow, discord shell
removed — band 7 wires the message-event shell in ``sb/adapters`` and
sends the returned reply through the RC-21 ChannelEmitter):

    1. resolver:   policy.resolve_policy()        (should the bot reply?)
    2. router:     router.classify()              (registered route probes)
    3. cooldown:   policy.is_on_cooldown()        (real per-guild policy)
    4. preset:     the installable vetted-answer port (zero-model answer)
    5. feature:    feature_facts.gather()         (registered gatherers)
    6. stack:      instructions.assemble()        (memory + facts + contracts)
    7. gateway:    AIGateway.execute()            (never raises)
    8. grounding:  grounding.verify_and_regenerate_once()
    9. audit:      decision_audit.record()        (EXACTLY one row per call)

Every code path produces exactly one ai_decision_audit row — denial,
skip, preset, reply, degrade, block. Outbound reply text is redacted
(the S6 chokepoint) before it leaves the engine or enters memory. The
engine returns an :class:`NLOutcome`; it NEVER sends (check_egress owns
sends — the shell delivers ``reply_text`` through the emitter port and
then calls :func:`note_reply_delivered`).

Deterministic refusal floors register per task
(:func:`register_refusal_floor` — band 7 registers the versioned domain
refusals); the kernel default floor is a generic held-back notice.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from sb.kernel.ai import decision_audit, feature_facts, instructions, memory, policy, router
from sb.kernel.ai.contracts import (
    AIRequest,
    AIRequestContext,
    AIScope,
    PolicyDenialReason,
)
from sb.kernel.ai.gateway import AIGateway, get_default_gateway
from sb.kernel.ai.grounding import verify_and_regenerate_once
from sb.kernel.observability.redaction import redact_text

__all__ = [
    "NLMessage",
    "NLOutcome",
    "handle_message",
    "install_preset_lookup",
    "note_reply_delivered",
    "register_refusal_floor",
    "reset_nl_engine_for_tests",
]

logger = logging.getLogger("sb.kernel.ai.nl_engine")


@dataclass(frozen=True)
class NLMessage:
    """One inbound message, as the K8/band-7 shell presents it (already
    mention-resolved: ``text`` is the mention-stripped body, ``raw_text``
    what the user actually typed — memory records the raw form)."""

    guild_id: int
    channel_id: int
    category_id: int | None
    user_id: int
    message_id: int | None
    text: str
    raw_text: str
    is_mention: bool
    user_level: int = 0
    user_role_ids: tuple[int, ...] = ()
    is_fresh_user: bool = False
    author_is_bot: bool = False
    display_name: str | None = None
    bot_user_id: int | None = None
    scope: AIScope = AIScope.USER
    extra: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class NLOutcome:
    """What the engine decided. ``reply_text`` is non-None exactly when
    the shell should deliver a message (a model reply, a preset, or a
    deterministic refusal floor). ``decision``/``reason`` mirror the
    audit row. ``used_fresh_allowance`` tells the shell to call
    :func:`note_reply_delivered` with it after a successful send (the
    allowance is spent per DELIVERED reply, never per attempt)."""

    decision: str  # the audit vocabulary
    reason: str
    reply_text: str | None = None
    task: str = ""
    route: str = ""
    provider: str | None = None
    model: str | None = None
    used_fresh_allowance: bool = False


# --- Installable ports -------------------------------------------------------

#: lookup(guild_id, normalized_question) -> vetted answer text or None
#: (the shipped ai_preset_service layer — operator-authored exact-match
#: answers served with ZERO model call; fail-safe: None = model path).
PresetLookup = Callable[[int, str], Awaitable[str | None]]

_preset_lookup: PresetLookup | None = None


def install_preset_lookup(lookup: PresetLookup) -> None:
    global _preset_lookup
    _preset_lookup = lookup


#: floor(task_id, question) -> deterministic refusal/floor text.
FloorFn = Callable[[str, str], str]

_FLOORS: dict[str, FloorFn] = {}

_DEFAULT_FLOOR_TEXT = (
    "I couldn't verify that answer against my data, so I held it back. "
    "Try rephrasing, or ask about something more specific."
)


def register_refusal_floor(task_id: str, floor: FloorFn) -> None:
    _FLOORS[task_id] = floor


def _floor_text(task_id: str, question: str) -> str:
    floor = _FLOORS.get(task_id)
    if floor is None:
        return _DEFAULT_FLOOR_TEXT
    try:
        return floor(task_id, question)
    except Exception:  # noqa: BLE001 — a floor must never break the refusal
        logger.warning("nl_engine: refusal floor for %s raised", task_id, exc_info=True)
        return _DEFAULT_FLOOR_TEXT


def reset_nl_engine_for_tests() -> None:
    global _preset_lookup
    _preset_lookup = None
    _FLOORS.clear()


def note_reply_delivered(
    guild_id: int,
    user_id: int,
    *,
    used_fresh_allowance: bool = False,
) -> None:
    """The shell calls this AFTER a successful send: charges the cooldown
    and (when the allow relied on it) one fresh-allowance unit."""
    policy.mark_reply_sent(guild_id, user_id)
    if used_fresh_allowance:
        policy.consume_fresh_allowance(guild_id, user_id)


# --- The engine ---------------------------------------------------------------


def _record_turn(msg: NLMessage) -> None:
    """Memory write (single deterministic owner): raw text, command-prefixed
    and bot-authored messages excluded (shipped rules)."""
    if msg.author_is_bot:
        return
    if msg.raw_text.startswith("!") or msg.raw_text.startswith("/"):
        return
    memory.conversation.append(
        msg.guild_id,
        msg.channel_id,
        user_id=msg.user_id,
        role="user",
        text=msg.raw_text,
        display_name=msg.display_name,
    )


async def _audit(
    msg: NLMessage,
    routed: router.RoutedTask | None,
    decision: str,
    reason: PolicyDenialReason | str,
    *,
    snapshot: str | None = None,
    profile_ids: list[int] | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> None:
    await decision_audit.record(
        guild_id=msg.guild_id,
        channel_id=msg.channel_id,
        category_id=msg.category_id,
        user_id=msg.user_id,
        message_id=msg.message_id,
        task=routed.task if routed else None,
        route=routed.route if routed else None,
        decision=decision,
        reason_code=reason,
        policy_snapshot_hash=snapshot,
        instruction_profile_ids=profile_ids,
        provider=provider,
        model=model,
    )


async def handle_message(
    msg: NLMessage,
    *,
    gateway: AIGateway | None = None,
    route_ctx: router.RouteContext | None = None,
) -> NLOutcome:
    """Run one message through the NL pipeline; never raises.

    The shell pre-filters empties and already-handled messages (shipped
    stage rules); the engine still guards the bare-mention empty case.
    """
    gw = gateway or get_default_gateway()

    # Bystander pre-record: non-mention messages enter memory whether or
    # not the bot replies; the triggering mention records AFTER the
    # recent-turn gather so it cannot appear in its own context.
    if not msg.is_mention:
        _record_turn(msg)

    ctx = policy.MessageContext(
        guild_id=msg.guild_id,
        channel_id=msg.channel_id,
        category_id=msg.category_id,
        user_id=msg.user_id,
        user_level=msg.user_level,
        user_role_ids=msg.user_role_ids,
        is_mention=msg.is_mention,
        is_fresh_user=msg.is_fresh_user,
    )
    decision = await policy.resolve_policy(ctx)

    # Route classification FIRST so the audit row records the routed task
    # even when denied (shipped ordering).
    routed = router.classify(
        msg.raw_text,
        route_ctx
        or router.RouteContext(guild_id=msg.guild_id, channel_id=msg.channel_id),
    )

    def _record_mention_turn() -> None:
        if msg.is_mention:
            _record_turn(msg)

    if not decision.allowed:
        _record_mention_turn()
        await _audit(
            msg,
            routed,
            "denied",
            decision.reason_code,
            snapshot=decision.policy_snapshot_hash,
            profile_ids=list(decision.instruction_profile_ids) or None,
        )
        return NLOutcome(
            decision="denied",
            reason=decision.reason_code.value,
            task=routed.task,
            route=routed.route,
        )

    if policy.is_on_cooldown(msg.guild_id, msg.user_id, decision.effective_cooldown):
        _record_mention_turn()
        await _audit(
            msg,
            routed,
            "denied",
            PolicyDenialReason.COOLDOWN_ACTIVE,
            snapshot=decision.policy_snapshot_hash,
        )
        return NLOutcome(
            decision="denied",
            reason=PolicyDenialReason.COOLDOWN_ACTIVE.value,
            task=routed.task,
            route=routed.route,
        )

    # Bare-mention guard: never send an empty current_user_message.
    if not msg.text.strip():
        _record_mention_turn()
        await _audit(
            msg,
            routed,
            "skipped",
            PolicyDenialReason.EMPTY_MESSAGE,
            snapshot=decision.policy_snapshot_hash,
            profile_ids=list(decision.instruction_profile_ids) or None,
        )
        return NLOutcome(
            decision="skipped",
            reason=PolicyDenialReason.EMPTY_MESSAGE.value,
            task=routed.task,
            route=routed.route,
        )

    # Vetted answer preset — the cheapest answer: exact-match, ZERO model
    # call; a miss/fault falls through byte-identical to the model path.
    if _preset_lookup is not None:
        preset_answer: str | None = None
        try:
            preset_answer = await _preset_lookup(msg.guild_id, msg.text)
        except Exception:  # noqa: BLE001 — preset faults never block a reply
            logger.warning("nl_engine: preset lookup raised", exc_info=True)
        if preset_answer:
            _record_mention_turn()
            await _audit(
                msg,
                routed,
                "replied",
                PolicyDenialReason.NONE,
                snapshot=decision.policy_snapshot_hash,
            )
            return NLOutcome(
                decision="replied",
                reason=PolicyDenialReason.NONE.value,
                reply_text=preset_answer,
                task=routed.task,
                route="preset",
                used_fresh_allowance=decision.used_fresh_allowance,
            )

    # Feature facts (registered gatherers) — gathered BEFORE the mention
    # records so carryover grounding sees exactly the prior turns.
    fact_req = feature_facts.FeatureFactRequest(
        task=routed.task,
        text=msg.raw_text,
        guild_id=msg.guild_id,
        channel_id=msg.channel_id,
        author_id=msg.user_id,
        message_id=msg.message_id,
        conversation_followup=routed.via_conversation_cue,
    )
    feature = await feature_facts.gather(fact_req)

    recent = await memory.gather_recent_turns(
        guild_id=msg.guild_id,
        channel_id=msg.channel_id,
    )
    _record_mention_turn()

    stack = await instructions.assemble(
        task_id=routed.task,
        guild_id=msg.guild_id,
        user_message=msg.text,
        profile_ids=decision.instruction_profile_ids,
        retrieved_facts=list(feature.facts),
        recent_turns=list(recent),
        bot_user_id=msg.bot_user_id,
    )

    def _request(extra_system: str = "") -> AIRequest:
        system = stack.render_system_prompt()
        if extra_system:
            system = f"{system}\n\n{extra_system}"
        return AIRequest(
            context=AIRequestContext(
                task=routed.task,
                scope=msg.scope,
                guild_id=msg.guild_id,
                actor_id=msg.user_id,
                channel_id=msg.channel_id,
            ),
            system_prompt=system,
            payload={"input": stack.render_payload_text()},
        )

    response = await gw.execute(_request())
    reply_text = redact_text((response.text or "").strip()).value

    if response.degraded or not reply_text:
        reason = (
            PolicyDenialReason.PROVIDER_UNAVAILABLE
            if response.degraded
            else PolicyDenialReason.NO_ROUTE_MATCHED
        )
        audit_decision = "degraded" if response.degraded else "skipped"
        await _audit(
            msg,
            routed,
            audit_decision,
            reason,
            snapshot=decision.policy_snapshot_hash,
            profile_ids=list(stack.instruction_profile_ids) or None,
            provider=response.provider or None,
            model=response.model or None,
        )
        return NLOutcome(
            decision=audit_decision,
            reason=reason.value,
            task=routed.task,
            route=routed.route,
            provider=response.provider or None,
            model=response.model or None,
        )

    # Faithfulness: registered verifier + the regenerate-once loop. The
    # registered domain verifier decides its own haystack policy; the
    # kernel passes facts ∪ (no tool ledger yet — the tool-loop ledger
    # rides the band-7 tool wiring).
    async def _regenerate(constraint: str) -> tuple[str, bool]:
        retry = await gw.execute(_request(extra_system=constraint))
        return redact_text((retry.text or "").strip()).value, retry.degraded

    outcome = await verify_and_regenerate_once(
        routed.task,
        reply_text,
        facts=tuple(feature.facts),
        regenerate=_regenerate,
    )

    if not outcome.grounded:
        if outcome.degraded:
            floor_decision = "degraded"
            floor_reason = PolicyDenialReason.PROVIDER_UNAVAILABLE
        else:
            floor_decision = "denied"
            floor_reason = PolicyDenialReason.GROUNDING_FAILED
        await _audit(
            msg,
            routed,
            floor_decision,
            floor_reason,
            snapshot=decision.policy_snapshot_hash,
            profile_ids=list(stack.instruction_profile_ids) or None,
            provider=response.provider or None,
            model=response.model or None,
        )
        return NLOutcome(
            decision=floor_decision,
            reason=floor_reason.value,
            reply_text=_floor_text(routed.task, msg.text),
            task=routed.task,
            route=routed.route,
            provider=response.provider or None,
            model=response.model or None,
        )

    final_text = outcome.reply_text
    # Remember the bot's own reply so follow-ups have the handle.
    memory.conversation.append(
        msg.guild_id,
        msg.channel_id,
        user_id=msg.user_id,
        role="assistant",
        text=final_text,
    )
    await _audit(
        msg,
        routed,
        "replied",
        PolicyDenialReason.NONE,
        snapshot=decision.policy_snapshot_hash,
        profile_ids=list(stack.instruction_profile_ids) or None,
        provider=response.provider or None,
        model=response.model or None,
    )
    return NLOutcome(
        decision="replied",
        reason=PolicyDenialReason.NONE.value,
        reply_text=final_text,
        task=routed.task,
        route=routed.route,
        provider=response.provider or None,
        model=response.model or None,
        used_fresh_allowance=decision.used_fresh_allowance,
    )

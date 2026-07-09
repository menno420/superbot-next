"""BTD6 K10 registrations (band 7) — everything the domain plugs into
the AI invocation kernel, per the K10 band map:

* legacy task ids ``btd6.answer`` + ``btd6.strategy_review`` claimed
  BYTE-IDENTICAL (``btd6.strategy_review`` is SONNET-RESERVED — owner
  ruling PR #30 K10(b)/D-0033; the routing table already pins
  claude-sonnet-4-6 on the id, no override here);
* the route probe (shipped ``ai_task_router.classify`` BTD6 leg:
  keyword fast-path, dataset entity-alias matcher with the possessive/
  plural fold, r-round shorthand, farm-money rescue, paragon-degree cue,
  MK-tower cue, conversation-cue follow-up, strategy-intake channel);
* the fact gatherer (``context.build`` → FeatureFactsResult);
* the grounding verifiers + paragon existence attribute (grounding.py);
* the versioned deterministic refusal floor;
* the BTD6 task-contract prose (the shipped playbook's grounding
  discipline, condensed to its normative directives);
* the A-17 eval suite (evals.py — 16 probes).

``register_btd6_ai()`` is called at manifest import + ENSURE_REFS
(idempotent), so any composition root that loads the manifest package
arms the domain."""

from __future__ import annotations

import re
import threading

from sb.domain.btd6 import dataset, keywords
from sb.kernel.ai import instructions, nl_engine, router, tasks

__all__ = ["btd6_probe", "register_btd6_ai"]

# ---------------------------------------------------------------------------
# Entity-alias cache (shipped _get_entity_aliases — lazy, dataset-backed)
# ---------------------------------------------------------------------------

_alias_lock = threading.Lock()
_entity_aliases: tuple[frozenset[str], frozenset[str]] | None = None
_tower_single_aliases: frozenset[str] | None = None


def _get_entity_aliases() -> tuple[frozenset[str], frozenset[str]]:
    """(multi_word_phrases, single_word_tokens) from the dataset. Multi
    matches as substring; single whole-word (distinctive hero + boss
    names only — single-word tower aliases are too generic)."""
    global _entity_aliases
    if _entity_aliases is not None:
        return _entity_aliases
    with _alias_lock:
        if _entity_aliases is not None:
            return _entity_aliases
        multi: set[str] = set()
        single: set[str] = set()
        try:
            for tower in dataset.towers():
                name = tower.canonical.lower()
                if " " in name:
                    multi.add(name)
            for hero in dataset.heroes():
                name = hero.canonical.lower()
                if " " in name:
                    multi.add(name)
                else:
                    single.add(name)
                for alias in hero.aliases:
                    al = alias.lower()
                    if " " in al:
                        multi.add(al)
                    elif len(al) > 4:
                        single.add(al)
            for boss in dataset.bosses():
                name = boss.canonical.lower()
                if " " in name:
                    multi.add(name)
                elif len(name) > 3:
                    single.add(name)
        except Exception:  # noqa: BLE001 — router stays fault-tolerant
            multi, single = set(), set()
        _entity_aliases = (frozenset(multi), frozenset(single))
        return _entity_aliases


def _get_tower_single_aliases() -> frozenset[str]:
    """Single-word tower names/aliases (>=4 chars) — a safe signal ONLY
    behind the Monkey-Knowledge cue (shipped)."""
    global _tower_single_aliases
    if _tower_single_aliases is not None:
        return _tower_single_aliases
    with _alias_lock:
        if _tower_single_aliases is not None:
            return _tower_single_aliases
        out: set[str] = set()
        try:
            for tower in dataset.towers():
                for surface in (tower.canonical, *tower.aliases):
                    s = surface.lower()
                    if " " not in s and len(s) >= 4:
                        out.add(s)
        except Exception:  # noqa: BLE001
            out = set()
        _tower_single_aliases = frozenset(out)
        return _tower_single_aliases


def reset_alias_cache_for_tests() -> None:
    global _entity_aliases, _tower_single_aliases
    with _alias_lock:
        _entity_aliases = None
        _tower_single_aliases = None


# ---------------------------------------------------------------------------
# The classify legs (shipped ai_task_router verbatim semantics)
# ---------------------------------------------------------------------------


def _looks_like_btd6_entity(lowered: str) -> bool:
    multi, single = _get_entity_aliases()
    if any(phrase in lowered for phrase in multi):
        return True
    if not single:
        return False
    raw = re.findall(r"[a-z0-9]+", lowered)
    tokens = frozenset(raw) | frozenset(
        t[:-1] for t in raw if len(t) > 4 and t.endswith("s")
    )
    return bool(tokens & single)


_MK_CUE_RE = re.compile(r"\bmonkey\s+knowledges?\b|\bmk\b", re.I)


def _looks_like_mk_tower_question(lowered: str) -> bool:
    if not _MK_CUE_RE.search(lowered):
        return False
    multi, _single = _get_entity_aliases()
    if any(phrase in lowered for phrase in multi):
        return True
    tokens = frozenset(re.findall(r"[a-z0-9]+", lowered))
    return bool(tokens & _get_tower_single_aliases())


_R_ROUND_RE = re.compile(r"\br\s?\d{1,3}\b")
_MONEY_CUE_RE = re.compile(
    r"\bcash\b|\bmoney\b|\bhow much\b|\bincome\b|\bearns?\b|\bearning\b",
)
_SHORT_ALIAS_MONEY_TOKENS = frozenset({"farm", "farms"})
_FOLLOWUP_PRONOUN_RE = re.compile(r"\b(?:it|its|they|them|those|these)\b")
_QUESTION_SHAPE_RE = re.compile(
    r"^(?:does|do|did|is|are|was|were|can|could|will|would|should|"
    r"what|how|why|when|which|who)\b|\?\s*$",
)


def _looks_like_round_shorthand(lowered: str) -> bool:
    hits = _R_ROUND_RE.findall(lowered)
    if len(hits) >= 2:
        return True
    return bool(hits) and _MONEY_CUE_RE.search(lowered) is not None


def _looks_like_short_alias_money(lowered: str) -> bool:
    if _MONEY_CUE_RE.search(lowered) is None:
        return False
    tokens = frozenset(re.findall(r"[a-z0-9]+", lowered))
    return bool(tokens & _SHORT_ALIAS_MONEY_TOKENS)


def _looks_like_conversation_followup(lowered: str) -> bool:
    stripped = lowered.strip()
    return bool(
        _FOLLOWUP_PRONOUN_RE.search(stripped) and _QUESTION_SHAPE_RE.search(stripped),
    )


def _looks_like_paragon_degree(lowered: str) -> bool:
    if keywords.degree_in_text(lowered) is None:
        return False
    if "paragon" in lowered:
        return True
    try:
        from sb.domain.btd6 import stats

        return stats.resolve_paragon_id(lowered) is not None
    except Exception:  # noqa: BLE001 — cue only, never break routing
        return False


def btd6_probe(text: str, ctx: router.RouteContext) -> router.RoutedTask | None:
    """The BTD6 leg of shipped ``classify()`` as a K10 RouteProbe."""
    lowered = (text or "").lower()
    via_cue = False
    looks_btd6 = any(keyword in lowered for keyword in keywords.BTD6_CONTEXT_KEYWORDS)
    if not looks_btd6:
        looks_btd6 = _looks_like_btd6_entity(lowered)
    if not looks_btd6:
        looks_btd6 = _looks_like_round_shorthand(lowered)
    if not looks_btd6:
        looks_btd6 = _looks_like_short_alias_money(lowered)
    if not looks_btd6:
        looks_btd6 = _looks_like_paragon_degree(lowered)
    if not looks_btd6:
        looks_btd6 = _looks_like_mk_tower_question(lowered)
    if not looks_btd6 and "btd6" in ctx.conversation_context_domains:
        looks_btd6 = via_cue = _looks_like_conversation_followup(lowered)
    if not looks_btd6:
        return None
    if "btd6_strategy" in ctx.intake_kinds:
        return router.RoutedTask(
            task="btd6.strategy_review",
            route="btd6.strategy_review",
            confidence=0.7,
        )
    return router.RoutedTask(
        task="btd6.answer",
        route="btd6.answer",
        confidence=0.6,
        via_conversation_cue=via_cue,
    )


# ---------------------------------------------------------------------------
# Registrations
# ---------------------------------------------------------------------------

# The shipped BTD6 playbook prose (ai_instruction_service _TASK_CONTRACT
# BTD6 sections), condensed to the normative directives.
_BTD6_TASK_CONTRACT = (
    "For Bloons TD 6 (BTD6): answer ONLY from the grounded '[btd6_*]' facts "
    "and approved tool results. When a fact line is tagged (e.g. "
    "'[btd6_tower]', '[btd6_boss]'), the name that follows IS the canonical "
    "name of that entity. NEVER invent or recall a specific BTD6 figure or "
    "ability from training data, even if an earlier turn stated it. 'dN' / "
    "'degree N' on a paragon is its DEGREE (1-100), never an upgrade path — "
    "paragons are tier 6, beyond the 0-5-5 cap. BTD6 prices scale with "
    "difficulty (Easy ×0.85 / Medium / Hard ×1.08 / Impoppable ×1.20, "
    "rounded to $5): quote the grounded per-difficulty figures verbatim and "
    "never derive your own totals. Treat '[btd6_coverage]' and "
    "'[btd6_freshness]' lines as the real limits of the data: without fresh "
    "live-event rows, say the live data isn't available rather than "
    "answering current boss/race/CT/odyssey questions from memory. If the "
    "data does not support an answer, say you don't have that information."
)


def register_btd6_ai() -> None:
    """Idempotent K10 wiring for the BTD6 knowledge domain."""
    assert "btd6.answer" in tasks.LEGACY_TASK_IDS
    assert "btd6.strategy_review" in tasks.LEGACY_TASK_IDS
    tasks.register_task(tasks.AITaskSpec(
        task_id="btd6.answer",
        owner_subsystem="btd6",
        description="Grounded BTD6 question answering over the committed "
                    "dataset (name+number+absence verified).",
        realtime=True,
        knowledge_domain="btd6",
    ))
    tasks.register_task(tasks.AITaskSpec(
        task_id="btd6.strategy_review",
        owner_subsystem="btd6",
        description="Review a submitted BTD6 strategy against grounded "
                    "facts (Sonnet-reserved — K10(b)/D-0033).",
        realtime=False,
        knowledge_domain="btd6",
    ))

    router.register_probe(router.RouteProbe(
        name="btd6",
        owner_subsystem="btd6",
        fn=btd6_probe,
        order=100,  # BTD6 before projmoon/video (shipped classify order)
    ))

    from sb.kernel.ai import feature_facts

    async def _gather(req: feature_facts.FeatureFactRequest):
        from sb.domain.btd6 import context

        ctx = await context.build(
            req.text,
            guild_id=req.guild_id,
            channel_id=req.channel_id,
            conversation_followup=req.conversation_followup,
        )
        return feature_facts.FeatureFactsResult(
            facts=ctx.facts, render_context=ctx,
        )

    if "btd6.answer" not in feature_facts.registered_gatherer_tasks():
        feature_facts.register_fact_gatherer(
            "btd6.answer", _gather, owner_subsystem="btd6",
        )
    if "btd6.strategy_review" not in feature_facts.registered_gatherer_tasks():
        feature_facts.register_fact_gatherer(
            "btd6.strategy_review", _gather, owner_subsystem="btd6",
        )

    from sb.domain.btd6 import context as _context
    from sb.domain.btd6 import grounding as _grounding

    _grounding.register_grounding()

    def _floor(task_id: str, question: str) -> str:
        return _context.no_data_refusal()

    nl_engine.register_refusal_floor("btd6.answer", _floor)
    nl_engine.register_refusal_floor("btd6.strategy_review", _floor)

    instructions.register_task_contract(
        "btd6.answer", owner_subsystem="btd6", text=_BTD6_TASK_CONTRACT,
    )
    instructions.register_task_contract(
        "btd6.strategy_review", owner_subsystem="btd6",
        text=_BTD6_TASK_CONTRACT,
    )

    from sb.domain.btd6 import evals as _evals

    _evals.register_eval_suite()

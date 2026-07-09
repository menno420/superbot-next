"""Project Moon K10 registrations (band 7) — the projmoon knowledge
domain onto the AI invocation kernel: the legacy id ``projmoon.answer``
claimed BYTE-IDENTICAL; the route probe = the shipped classify() Limbus
leg (``has_limbus_context``, checked AFTER BTD6 — order 110); the fact
gatherer (``context.build``); the names-only grounding verifier; the
deterministic refusal floor; the Limbus task contract; and the MINTED
12-probe A-17 eval suite (the oracle had none — A-17(d))."""

from __future__ import annotations

from sb.domain.projmoon import keywords
from sb.kernel.ai import instructions, nl_engine, router, tasks

__all__ = ["projmoon_probe", "register_projmoon_ai"]


def projmoon_probe(text: str, ctx: router.RouteContext) -> router.RoutedTask | None:
    """The Limbus leg of shipped ``classify()`` (confidence 0.6; curated
    low-false-positive keyword list — standalone non-Limbus chatter
    passes)."""
    if not keywords.has_limbus_context(text or ""):
        return None
    return router.RoutedTask(
        task="projmoon.answer",
        route="projmoon.answer",
        confidence=0.6,
    )


_PROJMOON_TASK_CONTRACT = (
    "For Project Moon (Limbus Company): answer ONLY from the grounded "
    "Limbus facts provided. The committed data is STRUCTURAL/lore "
    "(Sinners, Sins, damage types, E.G.O grades, statuses, combat "
    "mechanics) — exact numeric stats are NOT ingested, so never state a "
    "specific Limbus number as fact. Never misattribute a Sinner's "
    "literary origin or an E.G.O grade ordering — those are in the data; "
    "quote them. If the data does not support an answer, say you don't "
    "have that information."
)


def register_projmoon_ai() -> None:
    """Idempotent K10 wiring for the projmoon knowledge domain."""
    assert "projmoon.answer" in tasks.LEGACY_TASK_IDS
    tasks.register_task(tasks.AITaskSpec(
        task_id="projmoon.answer",
        owner_subsystem="projmoon",
        description="Grounded Project Moon (Limbus) question answering "
                    "over the committed structural fixtures (names-only "
                    "verified).",
        realtime=True,
        knowledge_domain="projmoon",
    ))

    router.register_probe(router.RouteProbe(
        name="projmoon",
        owner_subsystem="projmoon",
        fn=projmoon_probe,
        order=110,  # AFTER btd6 (shipped classify order), before video
    ))

    from sb.kernel.ai import feature_facts

    async def _gather(req: feature_facts.FeatureFactRequest):
        from sb.domain.projmoon import context

        ctx = context.build(req.text)
        return feature_facts.FeatureFactsResult(
            facts=ctx.facts, render_context=ctx,
        )

    if "projmoon.answer" not in feature_facts.registered_gatherer_tasks():
        feature_facts.register_fact_gatherer(
            "projmoon.answer", _gather, owner_subsystem="projmoon",
        )

    from sb.domain.projmoon import grounding as _grounding

    _grounding.register_grounding()

    def _floor(task_id: str, question: str) -> str:
        return _grounding.no_data_refusal()

    nl_engine.register_refusal_floor("projmoon.answer", _floor)

    instructions.register_task_contract(
        "projmoon.answer", owner_subsystem="projmoon",
        text=_PROJMOON_TASK_CONTRACT,
    )

    from sb.domain.projmoon import evals as _evals

    _evals.register_eval_suite()

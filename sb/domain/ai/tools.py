"""BTD6 factual tool rows (band 7) — the deterministic core of the
shipped ~35-row ``ai_tool_catalogue``/``ai_tools`` pair, registered on
the K10 tool registry with handler factories over the ported domain
(``grounding_domain="btd6"`` drives the derived grounding allowlist).

Rows carried (each backed by a real deterministic handler): btd6_lookup
· btd6_boss_lookup · btd6_power_lookup · btd6_monkey_knowledge_lookup ·
btd6_round_composition · btd6_round_cash · btd6_difficulty_cost ·
btd6_paragon_stats_at_degree. The rest of the shipped catalogue (maps/
modes/relic/geraldo/CT-live/superlative/capability/buff-uptime/server-
context/diagnostics/self-awareness/ticket rows) rides the deep-tools +
ingestion successor ports (D-0048) — their handlers' data layers aren't
aboard yet, and a registered tool without a real handler would be a
fabrication surface."""

from __future__ import annotations

from typing import Any

from sb.kernel.ai import tools_catalogue
from sb.kernel.ai.contracts import AIScope, AIToolMetadata, AIToolSpec

__all__ = ["register_btd6_tools"]

TOOLSET_BTD6_REFERENCE = "btd6_reference"
TOOLSET_BTD6_ROUNDS = "btd6_rounds"
TOOLSET_BTD6_COSTS = "btd6_costs"
TOOLSET_BTD6_PARAGON = "btd6_paragon"

_Q_PARAM = {
    "type": "object",
    "properties": {"query": {"type": "string"}},
    "required": ["query"],
}
_ROUND_PARAM = {
    "type": "object",
    "properties": {"round": {"type": "integer"},
                   "roundset": {"type": "string"}},
    "required": ["round"],
}


def _meta(*toolsets: str, cost: str = "cheap") -> AIToolMetadata:
    return AIToolMetadata(
        toolsets=frozenset(toolsets),
        task_affinity=frozenset({"btd6.answer", "btd6.strategy_review"}),
        grounding_domain="btd6",
        cost_class=cost,  # type: ignore[arg-type]
        freshness="static",
    )


def _text(facts) -> str:
    return "\n".join(facts) if facts else "no data on record"


def _lookup_factory(**_ctx: Any):
    async def handler(arguments: dict[str, Any]) -> Any:
        from sb.domain.btd6 import context

        ctx = await context.build(str(arguments.get("query") or ""))
        return {"facts": list(ctx.facts), "source": ctx.source_summary}
    return handler


def _boss_factory(**_ctx: Any):
    async def handler(arguments: dict[str, Any]) -> Any:
        from sb.domain.btd6 import context

        return _text(context._catalog_facts(  # noqa: SLF001 — same-band reuse
            str(arguments.get("query") or "") + " elite"))
    return handler


def _catalog_factory(**_ctx: Any):
    async def handler(arguments: dict[str, Any]) -> Any:
        from sb.domain.btd6 import context

        return _text(context._catalog_facts(  # noqa: SLF001
            str(arguments.get("query") or "")))
    return handler


def _mk_factory(**_ctx: Any):
    async def handler(arguments: dict[str, Any]) -> Any:
        from sb.domain.btd6 import context

        return _text(context._catalog_facts(  # noqa: SLF001
            "monkey knowledge " + str(arguments.get("query") or "")))
    return handler


def _round_factory(**_ctx: Any):
    async def handler(arguments: dict[str, Any]) -> Any:
        from sb.domain.btd6 import context

        roundset = str(arguments.get("roundset") or "default")
        abr = roundset.lower() == "abr"
        return _text(context._render_round(  # noqa: SLF001
            int(arguments.get("round") or 0), abr=abr))
    return handler


def _round_cash_factory(**_ctx: Any):
    async def handler(arguments: dict[str, Any]) -> Any:
        from sb.domain.ai import round_cash

        start = int(arguments.get("round_start") or 0)
        end = int(arguments.get("round_end") or start)
        roundset = str(arguments.get("roundset") or "default")
        total, missing = round_cash._range_cash(  # noqa: SLF001
            min(start, end), max(start, end), roundset)
        return {"range_cash": total, "missing_rounds": missing,
                "inclusive": True, "roundset": roundset}
    return handler


def _difficulty_cost_factory(**_ctx: Any):
    async def handler(arguments: dict[str, Any]) -> Any:
        from sb.domain.btd6 import difficulty_costs

        medium = int(arguments.get("medium_cost") or 0)
        return difficulty_costs.all_difficulty_costs(medium)
    return handler


def _paragon_degree_factory(**_ctx: Any):
    async def handler(arguments: dict[str, Any]) -> Any:
        from sb.domain.btd6 import context

        query = (f"{arguments.get('paragon') or ''} "
                 f"degree {arguments.get('degree') or ''}")
        return _text(context._paragon_degree_facts(query))  # noqa: SLF001
    return handler


_ROWS: tuple[tuple[str, str, dict, AIToolMetadata, Any], ...] = (
    ("btd6_lookup",
     "Ground a named BTD6 tower/hero/bloon/round/paragon: identity, "
     "costs, immunities, interactions.",
     _Q_PARAM, _meta(TOOLSET_BTD6_REFERENCE), _lookup_factory),
    ("btd6_boss_lookup",
     "Boss bloon facts incl. Standard AND Elite per-tier health tables.",
     _Q_PARAM, _meta(TOOLSET_BTD6_REFERENCE), _boss_factory),
    ("btd6_power_lookup",
     "A named Power's cost/limits/description.",
     _Q_PARAM, _meta(TOOLSET_BTD6_REFERENCE), _catalog_factory),
    ("btd6_monkey_knowledge_lookup",
     "A named Monkey Knowledge point's tree/effect/prerequisites.",
     _Q_PARAM, _meta(TOOLSET_BTD6_REFERENCE), _mk_factory),
    ("btd6_round_composition",
     "One round's composition, danger, RBE, and cash (standard or ABR).",
     _ROUND_PARAM, _meta(TOOLSET_BTD6_ROUNDS), _round_factory),
    ("btd6_round_cash",
     "Total round cash over an INCLUSIVE round range (standard or ABR).",
     {"type": "object",
      "properties": {"round_start": {"type": "integer"},
                     "round_end": {"type": "integer"},
                     "roundset": {"type": "string"}},
      "required": ["round_start", "round_end"]},
     _meta(TOOLSET_BTD6_ROUNDS, TOOLSET_BTD6_COSTS), _round_cash_factory),
    ("btd6_difficulty_cost",
     "Scale a Medium price to every difficulty (×0.85/1.08/1.20, "
     "rounded to $5).",
     {"type": "object",
      "properties": {"medium_cost": {"type": "integer"}},
      "required": ["medium_cost"]},
     _meta(TOOLSET_BTD6_COSTS), _difficulty_cost_factory),
    ("btd6_paragon_stats_at_degree",
     "A paragon's exact headline stats at a specific degree (1-100).",
     {"type": "object",
      "properties": {"paragon": {"type": "string"},
                     "degree": {"type": "integer"}},
      "required": ["paragon", "degree"]},
     _meta(TOOLSET_BTD6_PARAGON, cost="normal"), _paragon_degree_factory),
)


def register_btd6_tools() -> None:
    """Idempotent registration of the deterministic BTD6 tool rows."""
    registered = {t.spec.name for t in tools_catalogue.registered_tools()}
    for name, description, params, metadata, factory in _ROWS:
        if name in registered:
            continue
        tools_catalogue.register_tool(tools_catalogue.RegisteredTool(
            spec=AIToolSpec(name=name, description=description,
                            parameters=params, min_scope=AIScope.USER),
            metadata=metadata,
            owner_subsystem="ai",
            handler_factory=factory,
        ))

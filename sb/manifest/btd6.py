"""BTD6 subsystem manifest (band 7, knowledge-domain family) — the
shipped surface: !btd6menu (hub panel), the !btd6ref reference group
(tower/hero/round/income/rbe/relic/ct), the !btd6strat strategy group
(browse/mine/strategy/strategy-audit/submit/pending/strategies/
why-no-response), the !btd6events + !btd6ops groups (live-ingestion
subcommands = pending terminals; the ingestion subsystem is a named
successor port — D-0046), the strategy_submission_channel setting (the
route probe's strategy-intake cue), and the K10 registrations
(btd6.answer + Sonnet-reserved btd6.strategy_review, route probe, fact
gatherer, grounding verifiers + paragon existence attribute, refusal
floor, task contract, 16-probe A-17 eval suite)."""

from __future__ import annotations

from sb.domain.btd6 import ai_tasks as _ai_tasks
from sb.domain.btd6 import panels as _panels
from sb.domain.btd6 import service as _service
from sb.domain.btd6.ops import register_ops
from sb.domain.btd6.store import BTD6_STRATEGIES_STORE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef
from sb.spec.settings import SettingSpec

_SETTINGS = (
    SettingSpec(
        name="strategy_submission_channel", value_type=int, default=0,
        settings_key="btd6_strategy_submission_channel",
        capability_required="btd6.strategy.configure",
        hint="Channel bound as the BTD6 strategy intake — BTD6-looking "
             "messages there route to the Sonnet-reserved "
             "btd6.strategy_review task instead of btd6.answer.",
        input_hint="channel"),
)


def _ref(name: str, ref: str, summary: str, usage: str) -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX, group="btd6ref",
                       route=HandlerRef(ref), audience_tier="user",
                       capability="btd6", summary=summary, usage=usage)


def _strat(name: str, ref: str, summary: str,
           tier: str = "user") -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX,
                       group="btd6strat", route=HandlerRef(ref),
                       audience_tier=tier, capability="btd6",
                       summary=summary, usage=f"!btd6strat {name}")


def _events(name: str, ref: str, summary: str) -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX,
                       group="btd6events", route=HandlerRef(ref),
                       audience_tier="user", capability="btd6",
                       summary=summary, usage=f"!btd6events {name}")


def _ops(name: str, ref: str, summary: str) -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX,
                       group="btd6ops", route=HandlerRef(ref),
                       audience_tier="staff", capability="btd6",
                       summary=summary, usage=f"!btd6ops {name}")


MANIFEST = SubsystemManifest(
    key="btd6",
    version=1,
    commands=(
        CommandSpec(name="btd6menu", kind=CommandKind.PREFIX,
                    route=PanelRef("btd6.hub"), audience_tier="user",
                    capability="btd6",
                    summary="Open the BTD6 panel.", usage="!btd6menu"),
        CommandSpec(name="btd6ref", kind=CommandKind.PREFIX,
                    route=HandlerRef("btd6.ref_usage_view"),
                    audience_tier="user", capability="btd6",
                    summary="Deterministic BTD6 reference lookups.",
                    usage="!btd6ref <tower|hero|round|income|rbe|relic|ct>"),
        _ref("tower", "btd6.ref_tower_view",
             "Tower identity, costs (all difficulties), upgrades, paragon.",
             "!btd6ref tower <name>"),
        _ref("hero", "btd6.ref_hero_view",
             "Hero identity, cost, and ability list.",
             "!btd6ref hero <name>"),
        _ref("round", "btd6.ref_round_view",
             "Round composition, danger, RBE and cash.",
             "!btd6ref round <n> [abr]"),
        _ref("income", "btd6.ref_income_view",
             "Total round cash over an inclusive round range.",
             "!btd6ref income <from> <to>"),
        _ref("rbe", "btd6.ref_rbe_view",
             "Red Bloon Equivalent for a round.",
             "!btd6ref rbe <n> [abr]"),
        _ref("relic", "btd6.ref_relic_view",
             "A Contested Territory relic's static effect.",
             "!btd6ref relic <name>"),
        _ref("ct", "btd6.ref_ct_pending",
             "Live Contested Territory status (ingestion successor).",
             "!btd6ref ct"),
        CommandSpec(name="btd6strat", kind=CommandKind.PREFIX,
                    route=HandlerRef("btd6.strat_usage_view"),
                    audience_tier="user", capability="btd6",
                    summary="BTD6 strategy memory — submit, browse, review.",
                    usage="!btd6strat <submit|mine|browse|pending|"
                          "strategies|strategy|strategy-audit|"
                          "why-no-response>"),
        _strat("browse", "btd6.strat_browse_view",
               "This server's strategies."),
        _strat("mine", "btd6.strat_mine_view",
               "Strategies you submitted here."),
        _strat("strategy", "btd6.strat_detail_view",
               "One strategy in full."),
        _strat("strategy-audit", "btd6.strat_audit_view",
               "Where a strategy's transition audit lives."),
        _strat("submit", "btd6.strat_submit_route",
               "Submit a strategy: title | summary."),
        _strat("pending", "btd6.strat_pending_view",
               "Strategies awaiting review.", tier="staff"),
        _strat("strategies", "btd6.strat_published_view",
               "Published (cross-server) strategies."),
        _strat("why-no-response", "btd6.strat_why_view",
               "Recent btd6.answer routing decisions for this server."),
        CommandSpec(name="btd6events", kind=CommandKind.PREFIX,
                    route=HandlerRef("btd6.events_usage_view"),
                    audience_tier="user", capability="btd6",
                    summary="BTD6 live-event views (+ grounding check).",
                    usage="!btd6events <live|event|leaderboard|sources|"
                          "source-health|latest-data|refresh-source|"
                          "grounding>"),
        _events("live", "btd6.events_pending",
                "Current live events (ingestion successor)."),
        _events("event", "btd6.events_pending",
                "One live event in detail (ingestion successor)."),
        _events("leaderboard", "btd6.events_pending",
                "Live event leaderboard (ingestion successor)."),
        _events("sources", "btd6.events_pending",
                "Registered NK data sources (ingestion successor)."),
        _events("source-health", "btd6.events_pending",
                "Source freshness/health (ingestion successor)."),
        _events("latest-data", "btd6.events_pending",
                "Latest fetched envelopes (ingestion successor)."),
        _events("refresh-source", "btd6.events_pending",
                "Force-refresh one source (ingestion successor)."),
        _events("grounding", "btd6.events_grounding_view",
                "Show exactly what the retrieval grounds for a question."),
        CommandSpec(name="btd6ops", kind=CommandKind.PREFIX,
                    route=HandlerRef("btd6.ops_usage_view"),
                    audience_tier="staff", capability="btd6",
                    summary="BTD6 ingestion operations (successor port).",
                    usage="!btd6ops <readiness|runs|source_enable|"
                          "source_disable|seed-data>"),
        _ops("readiness", "btd6.ops_pending",
             "Ingestion readiness (successor port)."),
        _ops("runs", "btd6.ops_pending",
             "Recent ingestion runs (successor port)."),
        _ops("source_enable", "btd6.ops_pending",
             "Enable a data source (successor port)."),
        _ops("source_disable", "btd6.ops_pending",
             "Disable a data source (successor port)."),
        _ops("seed-data", "btd6.ops_pending",
             "Seed the data store from files (successor port)."),
    ),
    panels=(_panels.btd6_hub_spec(),),
    settings=_SETTINGS,
    stores=(BTD6_STRATEGIES_STORE,),
    events=(),
    capabilities=(),
)

register_ops()
_ai_tasks.register_btd6_ai()


def _ensure_refs() -> None:
    from sb.domain.btd6 import ops as _ops_mod
    from sb.domain.btd6 import store as _store

    _store.ensure_refs()
    _ops_mod.ensure_ops_refs()
    _panels.ensure_panel_refs()
    _service.ensure_handler_refs()
    register_ops()
    _ai_tasks.register_btd6_ai()


ENSURE_REFS = _ensure_refs

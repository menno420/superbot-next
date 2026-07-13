"""BTD6 subsystem manifest (band 7, knowledge-domain family) — the
shipped surface (oracle @7f7628e1, cogs/btd6/_unified.py: ONE ``!btd6``
tree, owner-picked "Flattest" layout 2026-06-24):

* ``!btd6`` (bare = the hub panel; same panel as ``!btd6menu``) with the
  flat lookups income/rbe/round/tower/estimate/hero/relic/ct/ask/status/
  diagnostics/test-intent/ctteam and the nested ``strat`` / ``ops`` /
  ``events`` groups — goldens/btd6 pins all 39 command shapes;
* the hidden-compat ``!btd6ref`` / ``!btd6strat`` / ``!btd6events`` /
  ``!btd6ops`` groups (the oracle kept them as muscle-memory aliases);
* the strategy_submission_channel + version_announce_channel settings;
* the K10 registrations (btd6.answer + Sonnet-reserved
  btd6.strategy_review, route probe, fact gatherer, grounding verifiers +
  paragon existence attribute, refusal floor, task contract, 16-probe
  A-17 eval suite).

Live ingestion (NK sources/facts/runs) is the named successor port
D-0046 — its command surfaces render the shipped EMPTY states, which are
also this build's true states."""

from __future__ import annotations

from sb.domain.btd6 import ai_tasks as _ai_tasks
from sb.domain.btd6 import oracle_surface as _oracle
from sb.domain.btd6 import panels as _panels
from sb.domain.btd6 import service as _service
from sb.domain.btd6.ops import register_ops
from sb.domain.btd6.store import BTD6_DATA_BLOBS_STORE, BTD6_STRATEGIES_STORE
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
    # NOTE: the version-announcement channel stays on the shipped
    # legacy-KV guild_settings lane (`!btd6 ops announcechannel` →
    # btd6.set_announce_channel op, key btd6_version_announcement_channel)
    # — the golden pins the row bytes; migrating it to a SettingSpec is
    # the settings-consolidation band's call, not this port's.
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


def _u(name: str, ref: str, summary: str, usage: str,
       group: str = "btd6", tier: str = "user") -> CommandSpec:
    """One node of the shipped unified `!btd6` tree."""
    return CommandSpec(name=name, kind=CommandKind.PREFIX, group=group,
                       route=HandlerRef(ref), audience_tier=tier,
                       capability="btd6", summary=summary, usage=usage)


_UNIFIED_TREE = (
    CommandSpec(name="btd6", kind=CommandKind.PREFIX,
                route=PanelRef("btd6.hub"), audience_tier="user",
                capability="btd6",
                summary="BTD6 Assistant — open the panel, or run a "
                        "subcommand (income/round/…).",
                usage="!btd6 [subcommand]"),
    # --- flat lookups (the everyday commands) ---
    _u("income", "btd6.cmd_income",
       "Verified cash per round — single round or an inclusive range.",
       "!btd6 income <round> [end_round]"),
    _u("rbe", "btd6.cmd_rbe",
       "RBE per round — single round or a range.",
       "!btd6 rbe <round> [end_round]"),
    _u("round", "btd6.cmd_round",
       "A single round's detail, or a values table across a range.",
       "!btd6 round <number> [end_round]"),
    _u("tower", "btd6.cmd_tower", "Look up a tower.",
       "!btd6 tower <name>"),
    _u("estimate", "btd6.cmd_estimate",
       "Estimate a boss fight: `<tower> vs <boss> [tier]`.",
       "!btd6 estimate [query]"),
    _u("hero", "btd6.cmd_hero", "Look up a hero.", "!btd6 hero <name>"),
    _u("relic", "btd6.cmd_relic",
       "CT relic effect + current tile (by name / abbrev / alias).",
       "!btd6 relic <name>"),
    _u("ct", "btd6.cmd_ct",
       "Browse active Contested Territory events and relic tiles.",
       "!btd6 ct"),
    _u("ask", "btd6.cmd_ask",
       "Deterministic Q&A (with optional AI augmentation).",
       "!btd6 ask <question>"),
    _u("status", "btd6.cmd_status", "BTD6 assistant status.",
       "!btd6 status"),
    _u("diagnostics", "btd6.cmd_diagnostics", "BTD6 dataset diagnostics.",
       "!btd6 diagnostics"),
    _u("test-intent", "btd6.cmd_test_intent",
       "Show what the resolver extracted from a message.",
       "!btd6 test-intent <text>"),
    _u("ctteam", "btd6.cmd_ctteam",
       "View or set this server's CT team.",
       "!btd6 ctteam [bracket id or group URL]"),
    # --- !btd6 strat … (strategy memory) ---
    _u("strat", "btd6.grp_bare",
       "BTD6 strategy memory (browse / submit / review).", "!btd6 strat"),
    _u("browse", "btd6.cmd_strat_browse",
       "Browse published BTD6 strategies.",
       "!btd6 strat browse [limit]", group="btd6.strat"),
    _u("mine", "btd6.cmd_strat_mine",
       "List my own strategy submissions in this guild.",
       "!btd6 strat mine [limit]", group="btd6.strat"),
    _u("strategy", "btd6.cmd_strat_strategy",
       "Show one strategy in detail.",
       "!btd6 strat strategy <id>", group="btd6.strat"),
    _u("strategy-audit", "btd6.cmd_strat_audit",
       "Per-strategy audit log.",
       "!btd6 strat strategy-audit <id>", group="btd6.strat"),
    _u("submit", "btd6.cmd_strat_submit",
       "Open a strategy submission modal (slash-only on Discord).",
       "!btd6 strat submit", group="btd6.strat"),
    _u("pending", "btd6.cmd_strat_pending",
       "List pending strategy submissions (staff-only).",
       "!btd6 strat pending [limit]", group="btd6.strat", tier="staff"),
    _u("strategies", "btd6.cmd_strat_strategies",
       "List strategy memory entries available in this guild.",
       "!btd6 strat strategies", group="btd6.strat"),
    _u("why-no-response", "btd6.cmd_strat_why",
       "Show the most recent BTD6 denials / skips for this guild.",
       "!btd6 strat why-no-response [limit]", group="btd6.strat"),
    # --- !btd6 ops … (ingestion operations; staff) ---
    _u("ops", "btd6.grp_bare",
       "BTD6 ingestion operations (staff readable; toggles are admin).",
       "!btd6 ops", tier="staff"),
    _u("readiness", "btd6.cmd_ops_readiness",
       "Show BTD6 ingestion readiness.",
       "!btd6 ops readiness", group="btd6.ops", tier="staff"),
    _u("runs", "btd6.cmd_ops_runs",
       "Show recent BTD6 ingestion runs.",
       "!btd6 ops runs [source_key] [limit]", group="btd6.ops",
       tier="staff"),
    _u("source_enable", "btd6.cmd_ops_source_enable",
       "Enable a BTD6 ingestion source (administrator only).",
       "!btd6 ops source_enable <source_key>", group="btd6.ops",
       tier="staff"),
    _u("source_disable", "btd6.cmd_ops_source_disable",
       "Disable a BTD6 ingestion source (administrator only).",
       "!btd6 ops source_disable <source_key>", group="btd6.ops",
       tier="staff"),
    _u("seed-data", "btd6.cmd_ops_seed",
       "Seed the Postgres data store from the bundled files (admin).",
       "!btd6 ops seed-data", group="btd6.ops", tier="staff"),
    _u("announcechannel", "btd6.cmd_ops_announcechannel",
       "Set/clear the BTD6 new-version announcement channel (admin).",
       "!btd6 ops announcechannel [#channel]", group="btd6.ops",
       tier="staff"),
    # --- !btd6 events … (live events / sources) ---
    _u("events", "btd6.grp_bare",
       "BTD6 live events, leaderboards, and data-source diagnostics.",
       "!btd6 events"),
    _u("live", "btd6.cmd_events_live",
       "Show recent live events (race/boss/ct/odyssey/event).",
       "!btd6 events live [kind] [limit]", group="btd6.events"),
    _u("event", "btd6.cmd_events_event",
       "Show one specific BTD6 event with tower restrictions.",
       "!btd6 events event <kind> <entity_key>", group="btd6.events"),
    _u("leaderboard", "btd6.cmd_events_leaderboard",
       "Top-N race or boss leaderboard.",
       "!btd6 events leaderboard <race|boss> [event_id] [limit]",
       group="btd6.events"),
    _u("sources", "btd6.cmd_events_sources",
       "List BTD6 source registry rows.",
       "!btd6 events sources", group="btd6.events"),
    _u("source-health", "btd6.cmd_events_source_health",
       "Show source registry freshness.",
       "!btd6 events source-health [limit]", group="btd6.events"),
    _u("latest-data", "btd6.cmd_events_latest",
       "Show newest fact envelope per entity_kind.",
       "!btd6 events latest-data", group="btd6.events"),
    _u("refresh-source", "btd6.cmd_events_refresh",
       "Manually refresh one Ninja Kiwi source (staff-only).",
       "!btd6 events refresh-source <source_key>", group="btd6.events",
       tier="staff"),
    _u("grounding", "btd6.cmd_events_grounding",
       "Show the grounding facts that fed an AI response.",
       "!btd6 events grounding <message_id>", group="btd6.events"),
)


MANIFEST = SubsystemManifest(
    key="btd6",
    version=1,
    commands=_UNIFIED_TREE + (
        CommandSpec(name="btd6menu", kind=CommandKind.PREFIX,
                    route=PanelRef("btd6.hub"), audience_tier="user",
                    capability="btd6",
                    summary="Open the BTD6 panel.", usage="!btd6menu"),
        # The shipped self-contained `!paragon` front door (oracle
        # cogs/paragon_cog.py — its OWN small cog, not a `!btd6` subcommand,
        # to keep the btd6 cog under the 800-LOC ceiling): opens the BTD6
        # Paragon degree calculator panel (goldens/btd6/sweep_paragon).
        CommandSpec(name="paragon", kind=CommandKind.PREFIX,
                    route=PanelRef("btd6.paragon"), audience_tier="user",
                    capability="btd6",
                    summary="Open the BTD6 Paragon degree calculator.",
                    usage="!paragon"),
        # The legacy alias trees below dispatch the SAME oracle handlers as
        # the unified `!btd6` tree — the goldens (sweep_btd6ref_* /
        # sweep_btd6strat_* / sweep_btd6events_* / sweep_btd6ops_*, re-homed
        # `_unmapped`→btd6) pin every alias byte-identical to its unified
        # sibling, and the bare group commands pin the shipped
        # send_help silence (grp_bare). The former invented usage-cards /
        # pending-terminal routes were band-5 shapes retired ORACLE-WINS
        # (the #193 re-home law).
        CommandSpec(name="btd6ref", kind=CommandKind.PREFIX,
                    route=HandlerRef("btd6.grp_bare"),
                    audience_tier="user", capability="btd6",
                    summary="Deterministic BTD6 reference lookups.",
                    usage="!btd6ref <tower|hero|round|income|rbe|relic|ct>"),
        _ref("tower", "btd6.cmd_tower",
             "Tower identity, costs (all difficulties), upgrades, paragon.",
             "!btd6ref tower <name>"),
        _ref("hero", "btd6.cmd_hero",
             "Hero identity, cost, and ability list.",
             "!btd6ref hero <name>"),
        _ref("round", "btd6.cmd_round",
             "Round composition, danger, RBE and cash.",
             "!btd6ref round <n> [abr]"),
        _ref("income", "btd6.cmd_income",
             "Total round cash over an inclusive round range.",
             "!btd6ref income <from> <to>"),
        _ref("rbe", "btd6.cmd_rbe",
             "Red Bloon Equivalent for a round.",
             "!btd6ref rbe <n> [abr]"),
        _ref("relic", "btd6.cmd_relic",
             "A Contested Territory relic's static effect.",
             "!btd6ref relic <name>"),
        _ref("ct", "btd6.cmd_ct",
             "Browse active Contested Territory events and relic tiles.",
             "!btd6ref ct"),
        CommandSpec(name="btd6strat", kind=CommandKind.PREFIX,
                    route=HandlerRef("btd6.grp_bare"),
                    audience_tier="user", capability="btd6",
                    summary="BTD6 strategy memory — submit, browse, review.",
                    usage="!btd6strat <submit|mine|browse|pending|"
                          "strategies|strategy|strategy-audit|"
                          "why-no-response>"),
        _strat("browse", "btd6.cmd_strat_browse",
               "This server's strategies."),
        _strat("mine", "btd6.cmd_strat_mine",
               "Strategies you submitted here."),
        _strat("strategy", "btd6.cmd_strat_strategy",
               "One strategy in full."),
        _strat("strategy-audit", "btd6.cmd_strat_audit",
               "Where a strategy's transition audit lives."),
        _strat("submit", "btd6.cmd_strat_submit",
               "Submit a strategy: title | summary."),
        _strat("pending", "btd6.cmd_strat_pending",
               "Strategies awaiting review.", tier="staff"),
        _strat("strategies", "btd6.cmd_strat_strategies",
               "Published (cross-server) strategies."),
        _strat("why-no-response", "btd6.cmd_strat_why",
               "Recent btd6.answer routing decisions for this server."),
        CommandSpec(name="btd6events", kind=CommandKind.PREFIX,
                    route=HandlerRef("btd6.grp_bare"),
                    audience_tier="user", capability="btd6",
                    summary="BTD6 live-event views (+ grounding check).",
                    usage="!btd6events <live|event|leaderboard|sources|"
                          "source-health|latest-data|refresh-source|"
                          "grounding>"),
        _events("live", "btd6.cmd_events_live",
                "Show recent live events (race/boss/ct/odyssey/event)."),
        _events("event", "btd6.cmd_events_event",
                "Show one specific BTD6 event with tower restrictions."),
        _events("leaderboard", "btd6.cmd_events_leaderboard",
                "Top-N race or boss leaderboard."),
        _events("sources", "btd6.cmd_events_sources",
                "List BTD6 source registry rows."),
        _events("source-health", "btd6.cmd_events_source_health",
                "Show source registry freshness."),
        _events("latest-data", "btd6.cmd_events_latest",
                "Show newest fact envelope per entity_kind."),
        _events("refresh-source", "btd6.cmd_events_refresh",
                "Manually refresh one Ninja Kiwi source (staff-only)."),
        _events("grounding", "btd6.cmd_events_grounding",
                "Show the grounding facts that fed an AI response."),
        CommandSpec(name="btd6ops", kind=CommandKind.PREFIX,
                    route=HandlerRef("btd6.grp_bare"),
                    audience_tier="staff", capability="btd6",
                    summary="BTD6 ingestion operations (staff readable; "
                            "toggles are admin).",
                    usage="!btd6ops <readiness|runs|source_enable|"
                          "source_disable|seed-data|announcechannel>"),
        _ops("readiness", "btd6.cmd_ops_readiness",
             "Show BTD6 ingestion readiness."),
        _ops("runs", "btd6.cmd_ops_runs",
             "Show recent BTD6 ingestion runs."),
        _ops("source_enable", "btd6.cmd_ops_source_enable",
             "Enable a BTD6 ingestion source (administrator only)."),
        _ops("source_disable", "btd6.cmd_ops_source_disable",
             "Disable a BTD6 ingestion source (administrator only)."),
        _ops("seed-data", "btd6.cmd_ops_seed",
             "Seed the Postgres data store from the bundled files (admin)."),
        _ops("announcechannel", "btd6.cmd_ops_announcechannel",
             "Set/clear the BTD6 new-version announcement channel (admin)."),
    ),
    panels=(_panels.btd6_hub_spec(), _panels.card_spec(),
            _panels.ctteam_spec(), _panels.strategy_submit_spec(),
            _panels.paragon_spec(), _panels.paragon_requirements_spec()),
    settings=_SETTINGS,
    stores=(BTD6_STRATEGIES_STORE, BTD6_DATA_BLOBS_STORE),
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
    _oracle.ensure_oracle_refs()
    register_ops()
    _ai_tasks.register_btd6_ai()


ENSURE_REFS = _ensure_refs

"""BTD6 oracle-surface HANDLERS (band 7) — the shipped ``!btd6`` unified
command tree (oracle ``cogs/btd6/_unified.py`` @7f7628e1), routed over the
card builders in :mod:`sb.domain.btd6.oracle_cards`.

Registered at MODULE IMPORT (declaring IS reserving — the BUG A rule,
sb/domain/role/handlers.py pattern): the live root imports and dispatches
without ever running the manifest ENSURE_REFS hooks.

Shipped semantics preserved:

* embed replies present through the ``btd6.card`` panel (public channel
  message on the prefix surface — the shipped ``ctx.send(embed=…)``);
* content-only replies stay plain sends;
* the bare group commands (``!btd6 strat`` / ``ops`` / ``events``) reply
  NOTHING — the shipped ``ctx.send_help`` produced no captured call
  (goldens/btd6/sweep_btd6_{strat,ops,events} pin the empty reply);
* ``!btd6`` bare opens the hub panel (same panel as ``!btd6menu``).

Unpinned deviations (no golden drives these paths) are ledgered in the
module they live in — see oracle_cards' module docstring for the list.
"""

from __future__ import annotations

import dataclasses

from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["ensure_oracle_refs"]


def _argv(req) -> list[str]:
    return [str(a) for a in tuple(req.args.get("argv", ()) or ())]


def _text(req) -> str:
    return " ".join(_argv(req)).strip() or str(req.args.get("name") or "").strip()


def _ints(req) -> list[int]:
    return [int(a) for a in _argv(req) if a.lstrip("-").isdigit()]


async def _card(req, embed) -> None:
    """Present one oracle card as the shipped public embed reply."""
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef("btd6.card"),
                     dataclasses.replace(
                         req, args={**dict(req.args), "_card": embed}))


def _ok(text: str) -> Reply:
    return Reply(SUCCESS, text)


# ---------------------------------------------------------------------------
# flat lookups
# ---------------------------------------------------------------------------


async def cmd_income(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    numbers = _ints(req)
    if not numbers:
        return _ok("Usage: `!btd6 income <round> [end_round]`.")
    await _card(req, cards.income_card(numbers[0],
                                       numbers[1] if len(numbers) > 1 else None))
    return None


async def cmd_rbe(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    numbers = _ints(req)
    if not numbers:
        return _ok("Usage: `!btd6 rbe <round> [end_round]`.")
    await _card(req, cards.rbe_card(numbers[0],
                                    numbers[1] if len(numbers) > 1 else None))
    return None


async def cmd_round(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    numbers = _ints(req)
    if not numbers:
        return _ok("Usage: `!btd6 round <number> [end_round]`.")
    await _card(req, cards.round_card(numbers[0],
                                      numbers[1] if len(numbers) > 1 else None))
    return None


async def cmd_tower(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    name = _text(req)
    if not name:
        return _ok("Usage: `!btd6 tower <name>`.")
    await _card(req, cards.tower_card(name))
    return None


async def cmd_hero(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    name = _text(req)
    if not name:
        return _ok("Usage: `!btd6 hero <name>`.")
    await _card(req, cards.hero_card(name))
    return None


async def cmd_ask(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    question = _text(req)
    if not question:
        return _ok("Usage: `!btd6 ask <question>`.")
    await _card(req, await cards.ask_card(question))
    return None


async def cmd_estimate(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    query = _text(req)
    if not query:
        await _card(req, cards.estimate_usage_card())
        return None
    # the deterministic boss-fight estimator service is a named successor
    # port — an honest terminal, never an invented number.
    return Reply(BLOCKED,
                 "🎯 The boss-fight estimator (HP/DPS/cost arithmetic) is "
                 "not armed in this build yet — `!btd6 estimate` shows the "
                 "query shapes it will take.")


async def cmd_relic(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    name = _text(req)
    if not name:
        return _ok("Usage: `!btd6 relic <name>`.")
    await _card(req, cards.relic_card(name))
    return None


async def cmd_ct(req) -> None:
    from sb.domain.btd6 import oracle_cards as cards

    await _card(req, cards.ct_browser_card())
    return None


async def cmd_ctteam(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    arg = _text(req)
    can_manage = bool(getattr(req.actor, "is_guild_operator", False))
    if arg:
        if not can_manage:
            from sb.kernel.panels.render import RenderedEmbed

            # the shipped _ct_team_notice (no ctx footer on notices)
            await _card(req, RenderedEmbed(
                title="🛡️ BTD6 — Your CT Team",
                description=("You need the Manage Server permission to "
                             "change the CT team."),
                style_token="gold"))
            return None
        # the guided set/clear flow writes the CT-team binding through the
        # live NK bracket preview — the ingestion successor port (D-0046).
        return Reply(BLOCKED,
                     "🛡️ Setting the CT team needs the live Ninja Kiwi "
                     "bracket preview (ingestion successor port) — not "
                     "armed in this build.")
    await open_panel(PanelRef("btd6.ctteam"),
                     dataclasses.replace(
                         req, args={**dict(req.args),
                                    "can_manage": can_manage}))
    return None


async def cmd_status(req) -> None:
    from sb.domain.btd6 import oracle_cards as cards

    await _card(req, cards.status_card())
    return None


async def cmd_diagnostics(req) -> None:
    from sb.domain.btd6 import oracle_cards as cards

    await _card(req, cards.diagnostics_card())
    return None


async def cmd_test_intent(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    text = _text(req)
    if not text:
        return _ok("Usage: `!btd6 test-intent <text>`.")
    await _card(req, cards.test_intent_card(text))
    return None


async def grp_bare(req) -> None:
    """The bare group commands (`!btd6 strat` / `ops` / `events`): the
    shipped ``ctx.send_help(ctx.command)`` produced no captured reply —
    the goldens pin the silence."""
    return None


# ---------------------------------------------------------------------------
# strat
# ---------------------------------------------------------------------------


async def cmd_strat_browse(req) -> None:
    from sb.domain.btd6 import oracle_cards as cards

    numbers = _ints(req)
    await _card(req, await cards.browse_card(numbers[0] if numbers else 10))
    return None


async def cmd_strat_mine(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    if not req.guild_id:
        return _ok("This command requires a guild context.")
    numbers = _ints(req)
    await _card(req, await cards.mine_card(
        int(req.guild_id), int(getattr(req.actor, "user_id", 0) or 0),
        numbers[0] if numbers else 10))
    return None


async def cmd_strat_strategy(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    numbers = _ints(req)
    if not numbers:
        return _ok("Usage: `!btd6 strat strategy <id>`.")
    payload = await cards.detail_card(
        numbers[0], viewer_guild_id=int(req.guild_id) if req.guild_id else None)
    if isinstance(payload, str):
        return _ok(payload)
    await _card(req, payload)
    return None


async def cmd_strat_audit(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    numbers = _ints(req)
    if not numbers:
        return _ok("Usage: `!btd6 strat strategy-audit <id>`.")
    await _card(req, await cards.audit_card(numbers[0]))
    return None


async def cmd_strat_submit(req) -> Reply:
    # the shipped prefix copy, verbatim — the write flow is the slash modal.
    return _ok("Strategy submission opens a Discord modal — use "
               "`/btd6 strat submit` to fill it in.")


async def cmd_strat_pending(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    if not req.guild_id:
        return _ok("This command requires a guild context.")
    numbers = _ints(req)
    payload = await cards.pending_payload(int(req.guild_id),
                                          numbers[0] if numbers else 5)
    if isinstance(payload, str):
        return _ok(payload)
    # rows pending: the shipped per-row review views ride the existing
    # `!btd6strat pending` staff surface; here the compact list keeps the
    # command honest without duplicating the review lane.
    return _ok("\n".join(cards._summarize_row(row) for row in payload))


async def cmd_strat_strategies(req) -> Reply:
    from sb.domain.btd6 import oracle_cards as cards

    if not req.guild_id:
        return _ok("This command requires a guild context.")
    return _ok(await cards.strategies_payload(int(req.guild_id)))


async def cmd_strat_why(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    if not req.guild_id:
        return _ok("This command requires a guild context.")
    numbers = _ints(req)
    payload = await cards.why_no_response_payload(
        int(req.guild_id), numbers[0] if numbers else 10)
    if isinstance(payload, str):
        return _ok(payload)
    await _card(req, payload)
    return None


# ---------------------------------------------------------------------------
# ops
# ---------------------------------------------------------------------------


async def cmd_ops_readiness(req) -> None:
    from sb.domain.btd6 import oracle_cards as cards

    await _card(req, cards.readiness_card())
    return None


async def cmd_ops_runs(req) -> None:
    from sb.domain.btd6 import oracle_cards as cards

    argv = _argv(req)
    source_key = argv[0] if argv and not argv[0].isdigit() else None
    await _card(req, cards.runs_card(source_key))
    return None


def _toggle_source_reply(source_key: str) -> Reply:
    # with zero sources registered (ingestion successor), every key is
    # unknown — the shipped InvalidSourceValueError copy, verbatim.
    return Reply(BLOCKED,
                 f"⚠️ unknown source_key={source_key.strip()!r}; "
                 "create it first")


async def cmd_ops_source_enable(req) -> Reply:
    argv = _argv(req)
    if not argv:
        return _ok("Usage: `!btd6 ops source_enable <source_key>`.")
    return _toggle_source_reply(argv[0])


async def cmd_ops_source_disable(req) -> Reply:
    argv = _argv(req)
    if not argv:
        return _ok("Usage: `!btd6 ops source_disable <source_key>`.")
    return _toggle_source_reply(argv[0])


async def cmd_ops_seed(req) -> Reply:
    return Reply(BLOCKED,
                 "🌱 The Postgres data-blob store (`btd6_data_blobs` seed) "
                 "is the ingestion successor port — this build serves the "
                 "committed dataset files directly.")


async def cmd_ops_announcechannel(req) -> Reply:
    """`!btd6 ops announcechannel [#channel]` — the shipped legacy-KV
    guild_settings write through the audited ``btd6.set_announce_channel``
    op (no channel = clear, value "" — the golden-pinned leg)."""
    import re

    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    argv = _argv(req)
    channel_id: int | None = None
    if argv:
        m = re.match(r"^<#(\d{15,20})>$|^(\d{15,20})$", argv[0])
        if m is None:
            return Reply(BLOCKED,
                         "That doesn't look like a channel — mention it "
                         "(`#channel`) or pass its id.")
        channel_id = int(m.group(1) or m.group(2))
    result = await engine.run(
        WorkflowRef("btd6.set_announce_channel"),
        _ctx_from_req(req, {"channel_id": channel_id}))
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     result.user_message or "Couldn't update the setting.")
    if channel_id is None:
        # shipped copy verbatim (btd6_version_announce.clear leg)
        return _ok("✅ BTD6 version announcements disabled (no channel set).")
    return _ok(f"✅ New BTD6 versions will be announced in <#{channel_id}>.")


# ---------------------------------------------------------------------------
# events
# ---------------------------------------------------------------------------


async def cmd_events_live(req) -> None:
    from sb.domain.btd6 import oracle_cards as cards

    argv = _argv(req)
    kind = argv[0] if argv else "race"
    await _card(req, cards.live_events_card(kind))
    return None


async def cmd_events_event(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    argv = _argv(req)
    if len(argv) < 2:
        return _ok("Usage: `!btd6 events event <kind> <entity_key>`.")
    await _card(req, cards.event_detail_card(argv[0], argv[1]))
    return None


async def cmd_events_leaderboard(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    argv = _argv(req)
    if not argv:
        return _ok("Usage: `!btd6 events leaderboard <race|boss> "
                   "[event_id] [limit]`.")
    event_id = argv[1] if len(argv) > 1 and not argv[1].isdigit() else None
    await _card(req, cards.leaderboard_card(argv[0], event_id))
    return None


async def cmd_events_sources(req) -> Reply:
    # zero registered sources — the shipped empty-list line, verbatim.
    return _ok("No BTD6 sources registered yet.")


async def cmd_events_source_health(req) -> None:
    from sb.domain.btd6 import oracle_cards as cards

    await _card(req, cards.source_health_card())
    return None


async def cmd_events_latest(req) -> None:
    from sb.domain.btd6 import oracle_cards as cards

    await _card(req, cards.latest_data_card())
    return None


async def cmd_events_refresh(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    argv = _argv(req)
    if not argv:
        return _ok("Usage: `!btd6 events refresh-source <source_key>`.")
    await _card(req, cards.refresh_source_card(argv[0]))
    return None


async def cmd_events_grounding(req) -> Reply | None:
    from sb.domain.btd6 import oracle_cards as cards

    if not req.guild_id:
        return _ok("This command requires a guild context.")
    argv = _argv(req)
    if not argv or not argv[0].lstrip("-").isdigit():
        return Reply(BLOCKED,
                     f"❌ Invalid message_id: {argv[0] if argv else ''!r}")
    payload = await cards.grounding_payload(int(req.guild_id), int(argv[0]))
    if isinstance(payload, str):
        return _ok(payload)
    await _card(req, payload)
    return None


# ---------------------------------------------------------------------------
# registration — MODULE IMPORT (BUG A rule)
# ---------------------------------------------------------------------------


_HANDLERS = (
    ("btd6.cmd_income", cmd_income),
    ("btd6.cmd_rbe", cmd_rbe),
    ("btd6.cmd_round", cmd_round),
    ("btd6.cmd_tower", cmd_tower),
    ("btd6.cmd_hero", cmd_hero),
    ("btd6.cmd_ask", cmd_ask),
    ("btd6.cmd_estimate", cmd_estimate),
    ("btd6.cmd_relic", cmd_relic),
    ("btd6.cmd_ct", cmd_ct),
    ("btd6.cmd_ctteam", cmd_ctteam),
    ("btd6.cmd_status", cmd_status),
    ("btd6.cmd_diagnostics", cmd_diagnostics),
    ("btd6.cmd_test_intent", cmd_test_intent),
    ("btd6.grp_bare", grp_bare),
    ("btd6.cmd_strat_browse", cmd_strat_browse),
    ("btd6.cmd_strat_mine", cmd_strat_mine),
    ("btd6.cmd_strat_strategy", cmd_strat_strategy),
    ("btd6.cmd_strat_audit", cmd_strat_audit),
    ("btd6.cmd_strat_submit", cmd_strat_submit),
    ("btd6.cmd_strat_pending", cmd_strat_pending),
    ("btd6.cmd_strat_strategies", cmd_strat_strategies),
    ("btd6.cmd_strat_why", cmd_strat_why),
    ("btd6.cmd_ops_readiness", cmd_ops_readiness),
    ("btd6.cmd_ops_runs", cmd_ops_runs),
    ("btd6.cmd_ops_source_enable", cmd_ops_source_enable),
    ("btd6.cmd_ops_source_disable", cmd_ops_source_disable),
    ("btd6.cmd_ops_seed", cmd_ops_seed),
    ("btd6.cmd_ops_announcechannel", cmd_ops_announcechannel),
    ("btd6.cmd_events_live", cmd_events_live),
    ("btd6.cmd_events_event", cmd_events_event),
    ("btd6.cmd_events_leaderboard", cmd_events_leaderboard),
    ("btd6.cmd_events_sources", cmd_events_sources),
    ("btd6.cmd_events_source_health", cmd_events_source_health),
    ("btd6.cmd_events_latest", cmd_events_latest),
    ("btd6.cmd_events_refresh", cmd_events_refresh),
    ("btd6.cmd_events_grounding", cmd_events_grounding),
)


def _register() -> None:
    from sb.domain.operator_spine import pending_handler
    from sb.spec.refs import HandlerRef, handler, is_registered

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)
    pending_handler(
        "btd6.ctteam_set_pending",
        "🛡️ Setting the CT team needs the live Ninja Kiwi bracket preview "
        "(ingestion successor port) — not armed in this build.")


def ensure_oracle_refs() -> None:
    _register()


_register()

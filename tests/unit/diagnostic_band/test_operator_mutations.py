"""The diagnostic operator mutations (ORDER 017 fix slice): cmdlist
paging over the oracle-extracted 14-page capture registry, the 🚩 Flag
Manager select→detail + Enable/Disable guard ladder, the 🤖 Automation
panel pick + mutation guards, and the hub process-state trio (Bot
Status / System Info / Recent Errors) as live successor reads.

Oracle: menno420/superbot — disbot/views/diagnostic/flag_manager.py,
automation_panel.py, hub_panel.py, paginator.py +
services/diagnostic_helpers.py + core/runtime/feature_flags.py.
Golden safety: the bare opens of every touched panel must keep the
bytes goldens/diagnostic pins (sweep_list_commands_detailed,
sweep_platform_flag, sweep_platform_automation, sweep_diagnostics) —
asserted here against the golden JSON directly where the bytes moved
(command_catalog page 1)."""

from __future__ import annotations

import asyncio
import dataclasses
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

run = asyncio.run

REPO_ROOT = Path(__file__).resolve().parents[3]


def _ensure_refs():
    import sb.manifest.diagnostic as m

    m.ENSURE_REFS()


def _handler(name: str):
    from sb.spec.refs import HandlerRef, resolve as resolve_ref

    _ensure_refs()
    return resolve_ref(HandlerRef(name))


@dataclasses.dataclass
class Req:
    args: dict
    guild_id: int | None = 42
    channel_id: int | None = 7
    actor: object = dataclasses.field(default_factory=lambda: SimpleNamespace(
        user_id=7, member_tier="administrator"))


def _ctx(params: dict | None = None, *, guild_id: int | None = 42,
         user_id: int = 7):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=guild_id,
        actor=SimpleNamespace(user_id=user_id,
                              member_tier="administrator"),
        channel_id=7, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(),
        params=dict(params or {}))


@pytest.fixture(autouse=True)
def _clean_picks():
    from sb.domain.diagnostic import handlers

    handlers._flag_pick.clear()
    handlers._auto_pick.clear()
    yield
    handlers._flag_pick.clear()
    handlers._auto_pick.clear()


# --- cmdlist paging (the shipped _PaginatorView, pages 1-14) --------------------


class TestCommandListPaging:
    def test_the_extracted_registry_matches_the_golden_page1_bytes(self):
        """Page 1 of the oracle-extracted COMMAND_LIST_PAGES must be
        BYTE-IDENTICAL to the golden — the identity that certifies pages
        2-14 as the same capture registry's bytes."""
        from sb.domain.diagnostic.command_catalog import COMMAND_LIST_PAGES

        golden = json.loads(
            (REPO_ROOT / "parity/goldens/diagnostic/"
             "sweep_list_commands_detailed.json").read_text())
        embed = golden["steps"][0]["calls"][0]["payload"]["embeds"][0]
        assert COMMAND_LIST_PAGES[0][0] == embed["title"]
        assert [list(f) for f in COMMAND_LIST_PAGES[0][1]] == [
            [f["name"], f["value"]] for f in embed["fields"]]

    def test_fourteen_pages_four_cogs_each(self):
        from sb.domain.diagnostic.command_catalog import COMMAND_LIST_PAGES

        assert len(COMMAND_LIST_PAGES) == 14
        assert [len(fields) for _, fields in COMMAND_LIST_PAGES] == (
            [4] * 13 + [3])          # 55 cogs with commands at capture
        for index, (title, _) in enumerate(COMMAND_LIST_PAGES):
            assert title == f"Command List — Page {index + 1}/14"

    def _rendered(self, params):
        from sb.domain.diagnostic.panels import command_list_spec
        from sb.spec.refs import resolve as resolve_ref

        _ensure_refs()
        spec = command_list_spec()
        return run(resolve_ref(spec.renderer_override)(spec, _ctx(params)))

    def test_bare_open_renders_page1_prev_disabled(self):
        """The golden's bare open: page 1, ◀ Prev disabled, Next ▶
        enabled — byte-stable through the paging change."""
        rendered = self._rendered({})
        assert rendered.embed.title == "Command List — Page 1/14"
        by_id = {c.custom_id: c for c in rendered.components}
        assert by_id["diagnostic.command_list.cmdlist_prev"].disabled is True
        assert by_id["diagnostic.command_list.cmdlist_next"].disabled is False

    def test_middle_page_renders_both_buttons_enabled(self):
        rendered = self._rendered({"cmdlist_page": 5})
        assert rendered.embed.title == "Command List — Page 6/14"
        by_id = {c.custom_id: c for c in rendered.components}
        assert by_id["diagnostic.command_list.cmdlist_prev"].disabled is False
        assert by_id["diagnostic.command_list.cmdlist_next"].disabled is False

    def test_last_page_disables_next(self):
        from sb.domain.diagnostic.command_catalog import COMMAND_LIST_PAGES

        rendered = self._rendered({"cmdlist_page": 13})
        assert rendered.embed.title == "Command List — Page 14/14"
        assert rendered.embed.fields == tuple(
            (n, v, False) for n, v in COMMAND_LIST_PAGES[13][1])
        by_id = {c.custom_id: c for c in rendered.components}
        assert by_id["diagnostic.command_list.cmdlist_prev"].disabled is False
        assert by_id["diagnostic.command_list.cmdlist_next"].disabled is True

    def test_prev_next_step_and_clamp(self, monkeypatch):
        import sb.kernel.panels.engine as engine
        from sb.spec.outcomes import SUCCESS

        opened = []

        async def fake_open(ref, req):
            opened.append((ref.name, req.args.get("cmdlist_page")))

        monkeypatch.setattr(engine, "open_panel", fake_open)
        nxt = _handler("diagnostic.cmdlist_next")
        prv = _handler("diagnostic.cmdlist_prev")

        assert run(nxt(Req(args={"cmdlist_page": 0}))).outcome == SUCCESS
        assert run(nxt(Req(args={"cmdlist_page": 12}))).outcome == SUCCESS
        assert run(nxt(Req(args={"cmdlist_page": 13}))).outcome == SUCCESS
        assert run(prv(Req(args={"cmdlist_page": 1}))).outcome == SUCCESS
        assert run(prv(Req(args={})) ).outcome == SUCCESS   # bare → clamped
        assert opened == [("diagnostic.command_list", 1),
                          ("diagnostic.command_list", 13),
                          ("diagnostic.command_list", 13),   # clamped high
                          ("diagnostic.command_list", 0),
                          ("diagnostic.command_list", 0)]    # clamped low


# --- the 🚩 Flag Manager ---------------------------------------------------------


class TestFlagManager:
    def test_pick_stores_and_reopens_the_manager(self, monkeypatch):
        import sb.kernel.panels.engine as engine
        from sb.domain.diagnostic.handlers import flag_pick_for
        from sb.spec.outcomes import SUCCESS

        opened = []

        async def fake_open(ref, req):
            opened.append(ref.name)

        monkeypatch.setattr(engine, "open_panel", fake_open)
        reply = run(_handler("diagnostic.flag_pick")(
            Req(args={"values": ("bindings.primary",)})))
        assert reply.outcome == SUCCESS
        assert opened == ["diagnostic.flag_manager"]
        assert flag_pick_for(42, 7) == "bindings.primary"

    def test_stale_pick_value_answers_the_no_flags_copy(self, monkeypatch):
        import sb.kernel.panels.engine as engine
        from sb.spec.outcomes import BLOCKED

        async def fake_open(ref, req):
            raise AssertionError("must not reopen on a stale value")

        monkeypatch.setattr(engine, "open_panel", fake_open)
        reply = run(_handler("diagnostic.flag_pick")(
            Req(args={"values": ("no.such.flag",)})))
        assert reply.outcome == BLOCKED
        assert reply.user_message == "No flags are declared in this build."

    def test_overview_bytes_unchanged_without_a_pick(self):
        """Golden safety: sweep_platform_flag's bare open renders the
        SAME overview embed (no sweep ever clicks the select)."""
        from sb.domain.diagnostic.panels import (
            _FLAG_DESCRIPTION,
            _FLAG_FOOTER,
            flag_manager_spec,
        )
        from sb.spec.refs import resolve as resolve_ref

        _ensure_refs()
        spec = flag_manager_spec()
        rendered = run(resolve_ref(spec.renderer_override)(spec, _ctx()))
        assert rendered.embed.title == "🚩 Flag Manager"
        assert rendered.embed.description == _FLAG_DESCRIPTION
        assert rendered.embed.footer == _FLAG_FOOTER
        assert rendered.embed.fields == ()

    def test_detail_render_after_a_pick(self):
        from sb.domain.diagnostic import handlers
        from sb.domain.diagnostic.panels import flag_manager_spec
        from sb.spec.refs import resolve as resolve_ref

        _ensure_refs()
        handlers._flag_pick[(42, 7)] = "bindings.primary"
        spec = flag_manager_spec()
        rendered = run(resolve_ref(spec.renderer_override)(spec, _ctx()))
        assert rendered.embed.title == (
            "🚩 Bindings as primary source (internal rollout gate)")
        fields = {name: value for name, value, _ in rendered.embed.fields}
        assert fields["Key"] == "`bindings.primary`"
        assert fields["Audience"] == "`internal`"
        assert fields["Editable"] == "`per-guild`"
        assert fields["Default"] == "`off`"
        assert fields["Effective"] == "`off`"     # v1 truth: no override store
        assert fields["Source"] == "`default`"    # the shipped flags-card byte
        assert fields["Guild override"] == "`none`"
        assert fields["Removal target"] == "Phase 2b stable"
        assert "Inactive / no consumer" in fields["Notes"]

    def test_env_only_flag_detail_marks_env_only(self):
        from sb.domain.diagnostic import handlers
        from sb.domain.diagnostic.panels import flag_manager_spec
        from sb.spec.refs import resolve as resolve_ref

        _ensure_refs()
        handlers._flag_pick[(42, 7)] = "feature_flag.primary"
        spec = flag_manager_spec()
        rendered = run(resolve_ref(spec.renderer_override)(spec, _ctx()))
        fields = {name: value for name, value, _ in rendered.embed.fields}
        assert fields["Editable"] == "`env-only`"
        assert "Env-only" in fields["Notes"]

    def test_enable_guard_ladder(self):
        from sb.domain.diagnostic import handlers
        from sb.spec.outcomes import BLOCKED

        enable = _handler("diagnostic.flag_enable")

        # 1. no pick — the oracle copy verbatim.
        reply = run(enable(Req(args={})))
        assert reply.outcome == BLOCKED
        assert reply.user_message == ("Pick a flag from the dropdown "
                                      "before changing its state.")

        # 2. picked, but no guild context — the oracle copy verbatim.
        handlers._flag_pick[(0, 7)] = "bindings.primary"
        reply = run(enable(Req(args={}, guild_id=None)))
        assert reply.outcome == BLOCKED
        assert reply.user_message == ("Guild context is required to set "
                                      "a per-guild override.")

        # 3. env-only gate — the oracle refusal (no env-var pointer: v1
        #    reads no SUPERBOT_FF_* variable).
        handlers._flag_pick[(42, 7)] = "feature_flag.primary"
        reply = run(enable(Req(args={})))
        assert reply.outcome == BLOCKED
        assert "env-only / internal gate" in reply.user_message
        assert "SUPERBOT_FF" not in reply.user_message

        # 4. db-editable flag — the final no-consumer refusal (no silent
        #    no-op writes; v1 has no flag consumer at all).
        handlers._flag_pick[(42, 7)] = "settings.manager_cog.enabled"
        reply = run(enable(Req(args={})))
        assert reply.outcome == BLOCKED
        assert "has no consumer in this build" in reply.user_message

    def test_disable_shares_the_ladder(self):
        from sb.spec.outcomes import BLOCKED

        reply = run(_handler("diagnostic.flag_disable")(Req(args={})))
        assert reply.outcome == BLOCKED
        assert reply.user_message == ("Pick a flag from the dropdown "
                                      "before changing its state.")


# --- the 🤖 Automation panel ------------------------------------------------------


class TestAutomationPanel:
    def test_placeholder_pick_reopens_and_buttons_guard(self, monkeypatch):
        import sb.kernel.panels.engine as engine
        from sb.spec.outcomes import BLOCKED, SUCCESS

        opened = []

        async def fake_open(ref, req):
            opened.append(ref.name)

        monkeypatch.setattr(engine, "open_panel", fake_open)
        # the placeholder row's value is "0" — the oracle's own "no valid
        # selection" arithmetic (rule_id <= 0).
        reply = run(_handler("diagnostic.automation_rule_pick")(
            Req(args={"values": ("0",)})))
        assert reply.outcome == SUCCESS
        assert opened == ["diagnostic.automation_panel"]

        for name in ("diagnostic.automation_enable",
                     "diagnostic.automation_disable",
                     "diagnostic.automation_delete"):
            reply = run(_handler(name)(Req(args={})))
            assert reply.outcome == BLOCKED
            # the oracle copy verbatim.
            assert reply.user_message == ("Pick a rule from the dropdown "
                                          "first.")

    def test_stale_positive_id_answers_not_found(self, monkeypatch):
        import sb.kernel.panels.engine as engine
        from sb.spec.outcomes import BLOCKED

        async def fake_open(ref, req):
            pass

        monkeypatch.setattr(engine, "open_panel", fake_open)
        run(_handler("diagnostic.automation_rule_pick")(
            Req(args={"values": ("3",)})))
        reply = run(_handler("diagnostic.automation_delete")(Req(args={})))
        assert reply.outcome == BLOCKED
        assert reply.user_message == ("Rule `#3` no longer exists in this "
                                      "guild — hit Refresh to reload the "
                                      "rule list.")


# --- the hub process-state trio ---------------------------------------------------


def _card_of(monkeypatch, handler_name: str):
    """Drive a card handler and capture the RenderedEmbed it presents."""
    import sb.kernel.panels.engine as engine

    cards = []

    async def fake_open(ref, req):
        assert ref.name == "diagnostic.card"
        cards.append(req.args["_card"])

    monkeypatch.setattr(engine, "open_panel", fake_open)
    run(_handler(handler_name)(Req(args={})))
    (card,) = cards
    return card


class TestProcessStateTrio:
    def test_sysinfo_card_is_the_shipped_shape_live(self, monkeypatch):
        import platform

        card = _card_of(monkeypatch, "diagnostic.diag_sysinfo_view")
        assert card.title == "System Information"
        assert card.style_token == "teal"
        fields = {n: (v, inline) for n, v, inline in card.fields}
        assert fields["Python"] == (platform.python_version(), True)
        assert fields["OS"][0].startswith(platform.system())
        assert fields["Disk"][1] is False
        assert fields["Disk"][0].startswith("Total: ")
        assert " Used: " in fields["Disk"][0]
        assert " Free: " in fields["Disk"][0]

    def test_status_card_unarmed_census_is_honest_na(self, monkeypatch):
        from sb.domain.diagnostic import handlers, process_state

        monkeypatch.setattr(handlers, "_gateway_census_reader", None)
        monkeypatch.setattr(handlers, "_ws_latency_reader", None)

        async def instant_cpu(interval=1.0):
            return 3.7

        monkeypatch.setattr(process_state, "cpu_percent", instant_cpu)
        card = _card_of(monkeypatch, "diagnostic.diag_status_view")
        assert card.title == "Bot Status"
        assert card.style_token == "green"
        fields = {n: v for n, v, _ in card.fields}
        assert fields["Guilds"] == "n/a"
        assert fields["Members"] == "n/a"
        assert fields["Commands"] == "n/a"
        assert fields["Latency"] == "nan ms"      # unarmed reader — the
        # sweep_latency world's own byte
        assert fields["CPU"] == "3.7%"
        assert fields["RAM"].endswith("%") or fields["RAM"] == "n/a"
        assert fields["Uptime"].count(":") == 2   # H:MM:SS shape

    def test_status_card_armed_census_reads_live(self, monkeypatch):
        from sb.domain.diagnostic import handlers, process_state

        monkeypatch.setattr(
            handlers, "_gateway_census_reader",
            lambda: {"guilds": 1, "members": 5, "commands": 413})
        monkeypatch.setattr(handlers, "_ws_latency_reader",
                            lambda: 0.0421)

        async def instant_cpu(interval=1.0):
            return None                            # a non-Linux host

        monkeypatch.setattr(process_state, "cpu_percent", instant_cpu)
        card = _card_of(monkeypatch, "diagnostic.diag_status_view")
        fields = {n: v for n, v, _ in card.fields}
        assert fields["Guilds"] == "1"
        assert fields["Members"] == "5"
        assert fields["Commands"] == "413"
        assert fields["Latency"] == "42.1 ms"
        assert fields["CPU"] == "n/a"              # degraded read — never
        # an invented number

    def test_errors_card_empty_then_captures_an_error(self, monkeypatch):
        import logging

        from sb.domain.diagnostic import log_buffer

        log_buffer._reset_for_tests()
        card = _card_of(monkeypatch, "diagnostic.diag_errors_view")
        assert card.title == "Recent Logs"
        assert card.style_token == "dark_red"
        # the shipped empty copy, verbatim.
        assert card.description == "No logs found matching the criteria."
        assert card.fields == ()

        log_buffer.install()
        logging.getLogger("sb.tests.diagnostic").error("boom probe")
        card = _card_of(monkeypatch, "diagnostic.diag_errors_view")
        assert card.description == ""
        assert any(name.endswith("ERROR") and value == "boom probe"
                   for name, value, _ in card.fields)
        log_buffer._reset_for_tests()

    def test_process_state_reads_are_defensive(self):
        from sb.domain.diagnostic import process_state

        ram = process_state.ram_percent()
        assert ram is None or 0.0 <= ram <= 100.0
        assert isinstance(process_state.uptime_text(), str)
        cpu = run(process_state.cpu_percent(interval=0.05))
        assert cpu is None or 0.0 <= cpu <= 100.0


# --- wiring: every touched surface routes to a REGISTERED implementation ----------


def test_specs_route_to_the_implemented_handlers():
    from sb.domain.diagnostic.panels import (
        automation_panel_spec,
        command_list_spec,
        diagnostic_hub_spec,
        flag_manager_spec,
    )
    from sb.spec.refs import HandlerRef, is_registered

    _ensure_refs()
    hub = {a.action_id: a.handler for a in diagnostic_hub_spec().actions}
    assert hub["diag_status"] == HandlerRef("diagnostic.diag_status_view")
    assert hub["diag_sysinfo"] == HandlerRef("diagnostic.diag_sysinfo_view")
    assert hub["diag_errors"] == HandlerRef("diagnostic.diag_errors_view")

    cmdlist = {a.action_id: a.handler for a in command_list_spec().actions}
    assert cmdlist["cmdlist_prev"] == HandlerRef("diagnostic.cmdlist_prev")
    assert cmdlist["cmdlist_next"] == HandlerRef("diagnostic.cmdlist_next")

    flag = flag_manager_spec()
    assert flag.selectors[0].on_select == HandlerRef("diagnostic.flag_pick")
    flag_actions = {a.action_id: a.handler for a in flag.actions}
    assert flag_actions["pf_flag_enable"] == HandlerRef(
        "diagnostic.flag_enable")
    assert flag_actions["pf_flag_disable"] == HandlerRef(
        "diagnostic.flag_disable")

    auto = automation_panel_spec()
    assert auto.selectors[0].on_select == HandlerRef(
        "diagnostic.automation_rule_pick")
    auto_actions = {a.action_id: a.handler for a in auto.actions}
    assert auto_actions["pf_auto_enable"] == HandlerRef(
        "diagnostic.automation_enable")
    assert auto_actions["pf_auto_disable"] == HandlerRef(
        "diagnostic.automation_disable")
    assert auto_actions["pf_auto_delete"] == HandlerRef(
        "diagnostic.automation_delete")

    for ref in ("diagnostic.diag_status_view", "diagnostic.diag_sysinfo_view",
                "diagnostic.diag_errors_view", "diagnostic.cmdlist_prev",
                "diagnostic.cmdlist_next", "diagnostic.flag_pick",
                "diagnostic.flag_enable", "diagnostic.flag_disable",
                "diagnostic.automation_rule_pick",
                "diagnostic.automation_enable",
                "diagnostic.automation_disable",
                "diagnostic.automation_delete"):
        assert is_registered(HandlerRef(ref)), ref


def test_no_diagnostic_pending_terminals_remain():
    """The one-way flip (A-16): the four *_pending routes are GONE from
    the diagnostic handler surface — nothing may route to them."""
    from sb.spec.refs import HandlerRef, is_registered

    _ensure_refs()
    for stale in ("diagnostic.cmdlist_page_pending", "diagnostic.flag_pending",
                  "diagnostic.automation_pending", "diagnostic.diag_pending"):
        assert not is_registered(HandlerRef(stale)), stale

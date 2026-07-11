"""Band 3 slice 3 (the panel-action slice) — the shipped economy/treasury/
inventory panel interactions over the declarative grammar, plus the G-10
kernel arming it forced (modal-issued terminal, modal-root static routing,
provider-fed selector options)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import sb.kernel.lifecycle as lifecycle
from sb.kernel.authority import owner as owner_mod
from sb.kernel.interaction import cooldown as cooldown_mod
from sb.kernel.interaction.adapters import reset_adapter_ports_for_tests
from sb.kernel.interaction.predicates import reset_predicate_ports_for_tests
from sb.kernel.interaction.request import ActorRef, ResolveRequest, Surface, TargetRef
from sb.kernel.interaction.resolve import reset_resolver_ports_for_tests, resolve
from sb.kernel.panels import engine as panel_engine
from sb.kernel.panels.registry import clear_panels_for_tests, static_route
from sb.spec.outcomes import SUCCESS, ReplyVisibility

run = asyncio.run


@pytest.fixture(autouse=True)
def _clean_state():
    lifecycle.reset_for_tests()
    lifecycle.set_phase(lifecycle.Phase.RUNNING)
    owner_mod.reset_for_tests()
    cooldown_mod.reset_for_tests()
    reset_resolver_ports_for_tests()
    reset_predicate_ports_for_tests()
    reset_adapter_ports_for_tests()
    clear_panels_for_tests()
    panel_engine.reset_panel_engine_for_tests()
    yield
    lifecycle.reset_for_tests()
    owner_mod.reset_for_tests()
    cooldown_mod.reset_for_tests()
    reset_resolver_ports_for_tests()
    reset_predicate_ports_for_tests()
    reset_adapter_ports_for_tests()
    clear_panels_for_tests()
    panel_engine.reset_panel_engine_for_tests()


class FakeResponder:
    surface = Surface.COMPONENT

    def __init__(self, surface: Surface = Surface.COMPONENT):
        self.surface = surface
        self.acks: list[bool] = []
        self.denials: list[tuple[str, bool]] = []
        self.modals: list = []
        self.rendered: list = []
        self._committed = None

    def is_acked(self) -> bool:
        return bool(self.acks)

    def committed_visibility(self):
        return self._committed

    async def ack(self, *, ephemeral: bool) -> None:
        self.acks.append(ephemeral)
        self._committed = (ReplyVisibility.EPHEMERAL if ephemeral
                           else ReplyVisibility.PUBLIC)

    async def deny(self, message: str, *, ephemeral: bool) -> None:
        self.denials.append((message, ephemeral))

    async def open_modal(self, modal_ref) -> None:
        self.modals.append(modal_ref)

    async def open_confirm(self, prompt) -> None:
        pass

    async def render(self, result) -> None:
        self.rendered.append(result)


def _actor() -> ActorRef:
    return ActorRef(user_id=42, is_guild_operator=False, is_bot_owner=False,
                    is_dm=False, member_tier="administrator")


def _req(spec, *, surface=Surface.COMPONENT, args=None, responder=None,
         key="probe") -> ResolveRequest:
    return ResolveRequest(
        surface=surface, target=TargetRef(key=key, spec=spec), actor=_actor(),
        guild_id=42, channel_id=7, args=args or {},
        responder=responder or FakeResponder(surface), origin=object())


def _install_all_panels():
    from sb.domain.economy import panels as ep
    from sb.domain.inventory import panels as ip
    from sb.domain.treasury import panels as tp

    ep.install_economy_panels()
    ip.install_inventory_panels()
    tp.install_treasury_panels()


# --- registration + the shipped custom-id vocabulary --------------------------------

def test_shipped_custom_ids_pinned_verbatim():
    _install_all_panels()
    for cid, panel_id, component_id in (
            ("economy:daily", "economy.hub", "daily"),
            ("economy:work", "economy.hub", "work"),
            ("economy:shop", "economy.hub", "shop"),
            ("economy:balance", "economy.hub", "balance"),
            ("economy:inventory", "economy.hub", "inventory"),
            ("economy:jobs", "economy.hub", "jobs"),
            ("economy:treasury", "economy.hub", "treasury"),
            ("economy:overview", "economy.hub", "overview")):
        binding = static_route(cid)
        assert binding is not None, cid
        assert (binding.panel_id, binding.component_id) == (panel_id, component_id)
    # G-10: the modal's custom-id root routes the SUBMIT to the declaring action.
    modal_binding = static_route("treasury.contribute_form")
    assert modal_binding.panel_id == "treasury.hub"
    assert modal_binding.component_id == "contribute"


def test_economy_hub_layout_is_the_shipped_arrangement():
    from sb.domain.economy.panels import economy_hub_spec

    rows = economy_hub_spec().layout.pages[0].rows
    assert rows == (("daily", "work", "shop"),
                    ("balance", "inventory", "jobs", "treasury"),
                    ("overview",))


def test_selector_routes_are_the_audited_ops():
    from sb.domain.economy.panels import jobcenter_spec, shop_panel_spec
    from sb.spec.refs import WorkflowRef

    assert jobcenter_spec().selectors[0].route == WorkflowRef("economy.work")
    assert shop_panel_spec().selectors[0].route == WorkflowRef("economy.buy")
    # shop options are the STATIC coupled-namespace keys.
    from sb.domain.economy.catalogue import SHOP_ITEMS
    assert shop_panel_spec().selectors[0].options_source == tuple(SHOP_ITEMS)


# --- G-10: click issues the form; dispatch happens only on submit --------------------

def test_modal_click_issues_form_terminal_no_dispatch(monkeypatch):
    import importlib

    resolve_mod = importlib.import_module("sb.kernel.interaction.resolve")
    from sb.domain.treasury.panels import CONTRIBUTE_MODAL, treasury_hub_spec

    calls = []

    async def fail_run(route, ctx):
        calls.append(route)
        raise AssertionError("workflow must not run on the opening click")

    monkeypatch.setattr(resolve_mod.workflow_engine, "run", fail_run)
    action = treasury_hub_spec().actions[0]
    responder = FakeResponder()
    result = run(resolve(_req(action, responder=responder,
                              key="treasury.hub.contribute")))
    assert result.outcome == SUCCESS
    assert responder.modals == [CONTRIBUTE_MODAL]
    assert not calls and not responder.acks


def test_modal_submit_dispatches_with_field_args(monkeypatch):
    import importlib

    resolve_mod = importlib.import_module("sb.kernel.interaction.resolve")
    from sb.kernel.interaction.adapters.modal import request_from_modal
    from sb.spec.refs import WorkflowRef

    _install_all_panels()
    seen = {}

    async def fake_run(route, ctx):
        seen["route"] = route
        seen["params"] = dict(ctx.params)
        return SimpleNamespace(outcome=SUCCESS, user_message="ok",
                               reason=None)

    monkeypatch.setattr(resolve_mod.workflow_engine, "run", fake_run)
    interaction = SimpleNamespace(
        data={"custom_id": "treasury.contribute_form",
              "components": [{"components": [
                  {"custom_id": "amount", "value": "250"}]}]},
        guild=SimpleNamespace(id=42, owner_id=42),
        user=SimpleNamespace(id=42), channel_id=7, id=9)
    responder = FakeResponder(Surface.MODAL)
    req = request_from_modal(interaction, responder=responder)
    assert req is not None                      # static-table fallthrough found it
    assert req.surface is Surface.MODAL
    result = run(resolve(req))
    assert result.outcome == SUCCESS
    assert seen["route"] == WorkflowRef("treasury.contribute")
    assert seen["params"]["amount"] == "250"
    assert responder.acks                       # submit re-entry acks like AUTO
    assert not responder.modals                 # never re-opens the form


# --- the third arg spelling: select values reach the audited ops ----------------------

def test_selector_values_reach_job_and_item_extractors():
    from sb.domain.economy.ops import _item_from, _job_from
    from tests.unit.band3.test_band3_economy import _ctx

    assert _job_from(_ctx({"values": ("Miner",)})) == "miner"
    assert _item_from(_ctx({"values": ("Car",)})) == "car"
    # explicit param still wins; argv still works (prefix surface).
    assert _job_from(_ctx({"job": "chef", "values": ("miner",)})) == "chef"
    assert _job_from(_ctx({"argv": ("farmer",)})) == "farmer"


def test_amount_from_accepts_modal_string_and_rejects_shipped_copy():
    from sb.domain.treasury.ops import _amount_from
    from sb.kernel.interaction.errors import ValidatorError
    from tests.unit.band3.test_band3_economy import _ctx

    assert _amount_from(_ctx({"amount": "250"})) == 250
    with pytest.raises(ValidatorError) as exc:
        _amount_from(_ctx({"amount": "abc"}))
    assert "is not a whole number of coins" in str(exc.value)


# --- provider-fed selector options ----------------------------------------------------

def _panel_ctx(uid: int = 42, gid: int = 1):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(bot=None, guild_id=gid,
                        actor=SimpleNamespace(user_id=uid), channel_id=7,
                        origin=PanelOrigin.INTERACTION,
                        audience=Audience.INVOKER, locale=LocaleContext())


def test_jobcenter_selector_materializes_available_jobs(monkeypatch):
    from sb.domain.economy import service
    from sb.domain.economy.panels import jobcenter_spec
    from sb.kernel.panels.render import render_panel

    async def fake_available(user_id, guild_id):
        return ["janitor", "cashier"]

    monkeypatch.setattr(service, "available_jobs", fake_available)
    rendered = run(render_panel(jobcenter_spec(), _panel_ctx()))
    selector = next(c for c in rendered.components if c.kind == "selector")
    # rich options — the shipped _JobSelect rows (emoji+title label, the
    # base-pay description; goldens/economy/sweep_work pins the bytes).
    assert [o["value"] for o in selector.options] == ["janitor", "cashier"]
    assert selector.options[0]["label"] == "🧹 Janitor"
    assert selector.options[0]["description"] == (
        "Base pay: 50 🪙  |  +10 XP  |  Tier 1")
    assert not selector.disabled


def test_jobcenter_selector_empty_degrades_disabled(monkeypatch):
    from sb.domain.economy import service
    from sb.domain.economy.panels import jobcenter_spec
    from sb.kernel.panels.render import render_panel

    async def none_available(user_id, guild_id):
        return []

    monkeypatch.setattr(service, "available_jobs", none_available)
    rendered = run(render_panel(jobcenter_spec(), _panel_ctx()))
    selector = next(c for c in rendered.components if c.kind == "selector")
    assert selector.disabled and selector.options == ()
    assert "No jobs available" in selector.placeholder


# --- inventory panels -------------------------------------------------------------------

def test_inventory_hub_provider_renders_user_preview(monkeypatch):
    from sb.domain.inventory import panels as ip
    from sb.domain.inventory import service
    from sb.spec.refs import ProviderRef, resolve as resolve_ref

    ip.ensure_panel_refs()

    async def fake_grouped(user_id, guild_id):
        return {"Tools": [("toolkit", 1, {"rarity": "Uncommon",
                                          "emoji": "🔧", "type": "Job Unlock"})]}

    monkeypatch.setattr(service, "build_combined_inventory", fake_grouped)
    provider = resolve_ref(ProviderRef("inventory.hub_overview"))
    fields = run(provider(_panel_ctx()))
    assert "Tools" in fields[0][1] and "Toolkit" in fields[0][1]

    async def empty(user_id, guild_id):
        return {}

    monkeypatch.setattr(service, "build_combined_inventory", empty)
    fields = run(provider(_panel_ctx()))
    assert "No items yet" in fields[0][1]       # shipped empty copy


def test_inventory_detail_provider_groups_rarest_first(monkeypatch):
    from sb.domain.inventory import panels as ip
    from sb.domain.inventory import service
    from sb.spec.refs import ProviderRef, resolve as resolve_ref

    ip.ensure_panel_refs()

    async def fake_grouped(user_id, guild_id):
        return {"Tools": [
            ("toolkit", 2, {"rarity": "Uncommon", "emoji": "🔧",
                            "type": "Job Unlock"}),
            ("axe", 1, {"rarity": "Uncommon", "emoji": "🪓", "type": "Tool"}),
        ]}

    monkeypatch.setattr(service, "build_combined_inventory", fake_grouped)
    provider = resolve_ref(ProviderRef("inventory.items_tools"))
    lines = run(provider(_panel_ctx()))
    assert lines[0].startswith("__Uncommon (2)__")
    assert any("Toolkit" in ln for ln in lines[1:])
    # empty category → () → the ListBlock renders its empty_state.
    async def empty(user_id, guild_id):
        return {}
    monkeypatch.setattr(service, "build_combined_inventory", empty)
    assert run(provider(_panel_ctx())) == ()


def test_inventory_hub_actions_open_every_category():
    from sb.domain.inventory.panels import (
        _CATEGORIES,
        category_detail_specs,
        inventory_hub_spec,
    )
    from sb.spec.refs import PanelRef

    hub = inventory_hub_spec()
    assert len(hub.actions) == len(_CATEGORIES) == 7
    detail_ids = {s.panel_id for s in category_detail_specs()}
    for action in hub.actions:
        assert isinstance(action.handler, PanelRef)
        assert action.handler.name in detail_ids
    # detail panels declare the shipped sort/filter algebra as grammar data.
    tools = next(s for s in category_detail_specs()
                 if s.panel_id == "inventory.cat_tools")
    ls = tools.body[0].list_spec
    assert ls.sort_options == ("rarity", "quantity", "name")
    assert ls.default_sort == "rarity"
    assert tools.navigation.parent == PanelRef("inventory.hub")


# --- manifest routing -------------------------------------------------------------------

def test_shop_command_now_opens_the_panel():
    import sb.manifest.economy as m
    from sb.spec.refs import PanelRef

    shop = next(c for c in m.MANIFEST.commands if c.name == "shop")
    assert shop.route == PanelRef("economy.shop_panel")
    panel_ids = {p.panel_id for p in m.MANIFEST.panels}
    assert panel_ids == {"economy.hub", "economy.jobcenter",
                         "economy.shop_panel", "economy.daily_card",
                         "economy.wallet_card"}


def test_inventory_manifest_declares_detail_panels():
    import sb.manifest.inventory as m

    ids = {p.panel_id for p in m.MANIFEST.panels}
    assert "inventory.hub" in ids and "inventory.cat_tools" in ids
    assert len(ids) == 8

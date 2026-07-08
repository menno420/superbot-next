"""Shared fixtures for the S9b panel-runtime tests: clean panel/router/
engine/locale state per test + a spec factory."""

from __future__ import annotations

import pytest

import sb.kernel.lifecycle as lifecycle
from sb.kernel.authority import owner as owner_mod
from sb.kernel.interaction import cooldown as cooldown_mod
from sb.kernel.interaction.adapters import reset_adapter_ports_for_tests
from sb.kernel.interaction.adapters.component import reset_dynamic_dispatcher_for_tests
from sb.kernel.interaction.locale import reset_copy_resolver_for_tests
from sb.kernel.interaction.predicates import reset_predicate_ports_for_tests
from sb.kernel.interaction.request import ActorRef
from sb.kernel.interaction.resolve import reset_resolver_ports_for_tests
from sb.kernel.panels.engine import reset_panel_engine_for_tests
from sb.kernel.panels.registry import clear_panels_for_tests
from sb.kernel.panels.render import reset_render_ports_for_tests
from sb.kernel.panels.router import reset_router_for_tests
from sb.spec.panels import (
    ActionStyle,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
)


@pytest.fixture(autouse=True)
def _clean_panel_state():
    for reset in (clear_panels_for_tests, reset_router_for_tests,
                  reset_panel_engine_for_tests, reset_render_ports_for_tests,
                  reset_copy_resolver_for_tests, reset_resolver_ports_for_tests,
                  reset_predicate_ports_for_tests, reset_adapter_ports_for_tests,
                  reset_dynamic_dispatcher_for_tests,
                  owner_mod.reset_for_tests, cooldown_mod.reset_for_tests,
                  lifecycle.reset_for_tests):
        reset()
    lifecycle.set_phase(lifecycle.Phase.RUNNING)
    yield
    for reset in (clear_panels_for_tests, reset_router_for_tests,
                  reset_panel_engine_for_tests, reset_render_ports_for_tests,
                  reset_copy_resolver_for_tests, reset_resolver_ports_for_tests,
                  reset_predicate_ports_for_tests, reset_adapter_ports_for_tests,
                  reset_dynamic_dispatcher_for_tests,
                  owner_mod.reset_for_tests, cooldown_mod.reset_for_tests,
                  lifecycle.reset_for_tests):
        reset()


def make_action(action_id="do", label="Do it", **kw) -> PanelActionSpec:
    return PanelActionSpec(action_id=action_id, label=label, **kw)


def make_panel(panel_id="econ.shop", subsystem="economy", actions=(),
               selectors=(), layout=None, **kw) -> PanelSpec:
    if layout is None:
        ids = tuple(a.action_id for a in actions) + tuple(
            s.selector_id for s in selectors)
        layout = LayoutSpec(pages=(PageSpec(rows=(ids,)),) if ids else ())
    kw.setdefault("navigation", NavigationSpec())
    kw.setdefault("title", "Shop")
    return PanelSpec(panel_id=panel_id, subsystem=subsystem,
                     actions=tuple(actions), selectors=tuple(selectors),
                     layout=layout, **kw)


def make_actor(**kw) -> ActorRef:
    defaults = dict(user_id=1, is_guild_operator=False, is_bot_owner=False,
                    is_dm=False, member_tier="administrator")
    defaults.update(kw)
    return ActorRef(**defaults)


DANGER = ActionStyle.DANGER

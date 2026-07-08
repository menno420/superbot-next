"""Fixture grammar types for compiler tests (S3).

These stand in for the Gate-0-minted facet grammar (CommandSpec etc.) so the
9-pass pipeline is exercised at K2 before the facet folds land — the compiler
is duck-typed over facet fields (spec 01: P6 reads NAMED declared fields).
Role registrations are idempotent for identical re-registration.
"""

from dataclasses import dataclass, field

import pytest

from sb.spec.refs import PredicateRef, clear_ref_table
from sb.spec.roles import register_field_roles


@dataclass(frozen=True)
class CommandSpec:
    name: str
    surface: str = "both"            # "prefix" | "slash" | "both"
    group: str | None = None
    route: object = None             # PanelRef | HandlerRef
    cooldown: float | None = None
    effect: str = "read"             # read | mutating | external
    help_order: int = 0              # [A] — the arrangement-invariance probe field


@dataclass(frozen=True)
class ConfirmationSpec:
    typed_challenge: bool = False


@dataclass(frozen=True)
class PanelActionSpec:
    action_id: str
    handler: object = None
    destructive: bool = False
    confirm: ConfirmationSpec | None = None
    reversibility: str = "REVERSIBLE"
    effect: str = "read"
    cooldown: float | None = None
    mirrors: str | None = None
    visible_when: PredicateRef | None = None


@dataclass(frozen=True)
class ComponentSpec:
    action_id: str | None = None
    selector_id: str | None = None


@dataclass(frozen=True)
class NavigationSpec:
    home: str = "home"


@dataclass(frozen=True)
class PanelSpec:
    panel_id: str
    navigation: NavigationSpec | None = None
    actions: tuple = ()
    components: tuple = ()
    layout: tuple = ()               # [A]


@dataclass(frozen=True)
class StoreSpec:
    table: str
    sole_writer: object = None
    checkpoint_class: str = "ledger"
    invariant_tag: str | None = None
    stat_key: str | None = None


@dataclass(frozen=True)
class EventSpec:
    name: str
    observability_only: bool = False


@dataclass(frozen=True)
class LeaderboardSpec:
    stat_key: str


register_field_roles("CommandSpec", name="S", surface="S", group="S", route="S",
                     cooldown="S", effect="S", help_order="A")
register_field_roles("ConfirmationSpec", typed_challenge="S")
register_field_roles("PanelActionSpec", action_id="S", handler="S", destructive="S",
                     confirm="S", reversibility="S", effect="S", cooldown="S",
                     mirrors="S", visible_when="S")
register_field_roles("ComponentSpec", action_id="S", selector_id="S")
register_field_roles("NavigationSpec", home="S")
register_field_roles("PanelSpec", panel_id="S", navigation="S", actions="S",
                     components="S", layout="A")
register_field_roles("StoreSpec", table="S", sole_writer="S", checkpoint_class="S",
                     invariant_tag="S", stat_key="S")
register_field_roles("EventSpec", name="S", observability_only="S")
register_field_roles("LeaderboardSpec", stat_key="S")


@pytest.fixture(autouse=True)
def fresh_ref_table():
    """Each test registers its own refs; the module-global table is reset."""
    clear_ref_table()
    yield
    clear_ref_table()

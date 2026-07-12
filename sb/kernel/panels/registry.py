"""The panel registry + static custom-id table (K8/S9b — design-spec §3.4).

Registration runs the compile fences, then mints every component's
custom_id: a legacy ``custom_id_override`` survives VERBATIM (compat=True);
new ids follow ``<panel_id>.<component_id>``. Engine-injected nav slots
(help / hub-home / back / page-turn) mint their ids here too — nav ids are
OUTSIDE the layout search space (§2.4's permanent exemption) but INSIDE the
one static routing table, so both populations are byte-exact-unique at
registration and cannot race at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.kernel.panels.compile import PanelCompileError, check_panel
from sb.spec.panels import FOLLOW_PARENT, PanelSpec, SelectorSpec

__all__ = [
    "ComponentBinding",
    "NAV_HELP_ID",
    "NAV_HUB_ID_PREFIX",
    "NavBinding",
    "clear_panels_for_tests",
    "get_panel",
    "panel_inventory",
    "register_hub",
    "register_panel",
    "static_route",
]

# The frozen legacy nav constants (verbatim from disbot/views/navigation.py:58-59).
NAV_HELP_ID = "nav:help"
NAV_HUB_ID_PREFIX = "nav:hub:"
NAV_BACK_ID_PREFIX = "nav:back:"
NAV_PAGE_ID_PREFIX = "nav:page:"
# The shared BrowserView control family (D-0034) — the page-turn control's
# richer sibling. Its {sort × filter × page} state space is combinatorial, so
# these ids are PARSED at click time by the router (never pre-minted into the
# static table), but they stay inside the nav namespace and route through the
# ONE panel-engine seam. Grammar + codec live in sb.kernel.panels.browserview.
NAV_BROWSE_ID_PREFIX = "nav:browse:"
NAV_ROW = 4     # the shipped nav row


@dataclass(frozen=True)
class ComponentBinding:
    """One static-table entry for a declared action/selector."""

    panel_id: str
    component_id: str
    spec: object           # PanelActionSpec | SelectorSpec

    @property
    def is_selector(self) -> bool:
        return isinstance(self.spec, SelectorSpec)


@dataclass(frozen=True)
class NavBinding:
    """One static-table entry for an engine-injected nav slot."""

    kind: str              # "help" | "hub" | "back" | "page"
    target: str            # hub key | parent panel_id | "<panel_id>:<page>"


_PANELS: dict[str, PanelSpec] = {}
_STATIC_TABLE: dict[str, ComponentBinding | NavBinding] = {}
# hub key -> panel_id of the hub panel (every hub's nav:hub:<hub> constant
# stays registered for the hub's LIFETIME — the restart-compat rule §2.4).
_HUBS: dict[str, str] = {}


def _mint(custom_id: str, binding: ComponentBinding | NavBinding) -> None:
    existing = _STATIC_TABLE.get(custom_id)
    if existing is not None and existing != binding:
        raise PanelCompileError(
            "custom_id_collision",
            f"custom_id {custom_id!r} already bound to {existing} (new: {binding})")
    _STATIC_TABLE[custom_id] = binding


def register_hub(hub_key: str, panel_id: str) -> None:
    """Mint the hub-keyed ``nav:hub:<hub>`` constant (per HUB IDENTITY [S],
    never from parent_hub — reassigning a subsystem's hub changes which
    stable button its panels show, not any string)."""
    prior = _HUBS.get(hub_key)
    if prior is not None and prior != panel_id:
        raise PanelCompileError(
            "hub_redefined", f"hub {hub_key!r} already routes to {prior!r}")
    _HUBS[hub_key] = panel_id
    _mint(f"{NAV_HUB_ID_PREFIX}{hub_key}", NavBinding(kind="hub", target=hub_key))


def hub_panel_id(hub_key: str) -> str | None:
    return _HUBS.get(hub_key)


def register_panel(spec: PanelSpec) -> PanelSpec:
    """Fence → mint → table. Idempotent re-registration of the identical
    spec is a no-op; a differing spec under the same panel_id is an error."""
    prior = _PANELS.get(spec.panel_id)
    if prior is not None:
        if prior == spec:
            return spec
        raise PanelCompileError(
            "panel_redefined", f"panel {spec.panel_id!r} registered twice with differing specs")
    check_panel(spec)

    minted: list[tuple[str, ComponentBinding]] = []
    for action in spec.actions:
        cid = action.custom_id_override or f"{spec.panel_id}.{action.action_id}"
        minted.append((cid, ComponentBinding(spec.panel_id, action.action_id, action)))
        if action.modal is not None:
            # G-10: the modal's custom-id root routes the SUBMIT back to the
            # declaring action (the MODAL adapter's static-table fallthrough)
            # — the form is data, dispatch stays the action's handler.
            minted.append((action.modal.modal_id,
                           ComponentBinding(spec.panel_id, action.action_id, action)))
    for selector in spec.selectors:
        cid = selector.custom_id_override or f"{spec.panel_id}.{selector.selector_id}"
        minted.append((cid, ComponentBinding(spec.panel_id, selector.selector_id, selector)))
    for cid, binding in minted:
        _mint(cid, binding)

    # engine-owned nav ids for this panel (outside the layout search space).
    if spec.navigation.parent is not None:
        _mint(f"{NAV_BACK_ID_PREFIX}{spec.navigation.parent.name}",
              NavBinding(kind="back", target=spec.navigation.parent.name))
    for extra in spec.navigation.extra_routes:
        _mint(f"{NAV_BACK_ID_PREFIX}{extra.route.name}",
              NavBinding(kind="back", target=extra.route.name))
    page_count = max(len(spec.layout.pages), 1)
    if page_count > 1:
        for page in range(page_count):
            _mint(f"{NAV_PAGE_ID_PREFIX}{spec.panel_id}:{page}",
                  NavBinding(kind="page", target=f"{spec.panel_id}:{page}"))
    _mint(NAV_HELP_ID, NavBinding(kind="help", target="help"))

    _PANELS[spec.panel_id] = spec
    return spec


def get_panel(panel_id: str) -> PanelSpec:
    try:
        return _PANELS[panel_id]
    except KeyError:
        raise LookupError(f"no PanelSpec registered for {panel_id!r}") from None


def static_route(custom_id: str) -> ComponentBinding | NavBinding | None:
    """Router precedence step (1): exact match in the ONE static table."""
    return _STATIC_TABLE.get(custom_id)


def resolve_home_hub(spec: PanelSpec, subsystem_hub: str | None) -> str | None:
    """FOLLOW_PARENT resolution — the subsystem's CURRENT parent_hub at
    render/click time (§2.4); an explicit hub key is the rare semantic pin."""
    if spec.navigation.home_hub == FOLLOW_PARENT:
        return subsystem_hub
    return spec.navigation.home_hub or None


def panel_inventory() -> dict[str, PanelSpec]:
    return dict(_PANELS)


def static_table() -> dict[str, ComponentBinding | NavBinding]:
    return dict(_STATIC_TABLE)


def clear_panels_for_tests() -> None:
    _PANELS.clear()
    _STATIC_TABLE.clear()
    _HUBS.clear()

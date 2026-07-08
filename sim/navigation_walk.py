"""The A-3 navigation-completeness walker (canonical plan §5 step 11 —
the CI proof of Q-0231's Back+Home guarantee).

Drives the GENERATED hub through every declared node + the re-render path
using the real S9b panel engine (sb.kernel.panels), asserting per state:

  - reachability — every registered panel is reachable from a hub root via
    open-child edges, OR is a direct-entry panel with a declared semantic
    parent fallback (verification-review §3.4);
  - framework-injected working Back — a panel with a declared parent
    renders the `nav:back:<parent>` slot AND that slot is bound in the ONE
    static table AND the parent re-renders fresh;
  - framework-injected working Home — `show_home` panels with a resolvable
    hub render the `nav:hub:<hub>` slot, bound in the static table;
  - re-render stability — parent -> child -> parent again produces the
    identical component population (the in-place rerender survival check).

"Every feature in >=1 preset" is the golden's fourth leg; presets are
band-1 grammar and do not exist yet — the report carries
`presets_checked=False` LOUDLY until the preset facet lands (arm-later,
never silently green).

Consumed by tests/unit/navigation_golden/ (the CI golden) and re-run over
real manifests as port bands register panels.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sb.kernel.panels.registry import (
    NAV_BACK_ID_PREFIX,
    NAV_HUB_ID_PREFIX,
    panel_inventory,
    static_route,
)
from sb.kernel.panels.render import render_panel
from sb.spec.refs import PanelRef

__all__ = ["NavigationReport", "StateReport", "walk_navigation"]


@dataclass(frozen=True)
class StateReport:
    panel_id: str
    reachable: bool
    back_ok: bool | None      # None = no parent declared (nothing to check)
    home_ok: bool | None      # None = show_home False or no hub resolvable
    rerender_ok: bool | None  # None = no parent to hop from


@dataclass
class NavigationReport:
    states: dict[str, StateReport] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)
    presets_checked: bool = False   # arm-later: band-1 preset grammar

    @property
    def ok(self) -> bool:
        return not self.problems


def _component_population(rendered_pages) -> set[str]:
    return {
        component.custom_id
        for rendered in rendered_pages
        for component in rendered.components
    }


async def _render_all_pages(spec, ctx, subsystem_hub):
    pages = max(len(spec.layout.pages), 1)
    return [
        await render_panel(spec, ctx, page=page, subsystem_hub=subsystem_hub)
        for page in range(pages)
    ]


async def walk_navigation(ctx, *, subsystem_hubs: dict[str, str] | None = None) -> NavigationReport:
    """`ctx` is a PanelContext (the walker's persona); `subsystem_hubs`
    maps subsystem key -> hub key (the FOLLOW_PARENT resolution input —
    port bands pass their manifest-derived map)."""
    hubs = subsystem_hubs or {}
    report = NavigationReport()
    inventory = panel_inventory()

    # Reachability: roots = the registered hub panels; edges = open-child
    # PanelRef handlers + navigation extra routes.
    from sb.kernel.panels.registry import _HUBS  # noqa: PLC2701 - the one enumeration seam

    roots: set[str] = set(_HUBS.values())

    edges: dict[str, set[str]] = {pid: set() for pid in inventory}
    for panel_id, spec in inventory.items():
        for action in spec.actions:
            if isinstance(action.handler, PanelRef):
                edges[panel_id].add(action.handler.name)
        for extra in spec.navigation.extra_routes:
            edges[panel_id].add(extra.route.name)

    reachable: set[str] = set()
    frontier = [r for r in roots if r in inventory]
    while frontier:
        current = frontier.pop()
        if current in reachable:
            continue
        reachable.add(current)
        frontier.extend(c for c in edges.get(current, ()) if c in inventory)

    for panel_id, spec in sorted(inventory.items()):
        subsystem_hub = hubs.get(spec.subsystem)
        is_reachable = panel_id in reachable
        if not is_reachable and spec.navigation.parent is None and panel_id not in roots:
            report.problems.append(
                f"{panel_id}: unreachable from any hub root and no semantic "
                f"parent fallback (direct-entry panels need one, §3.4)"
            )

        rendered_pages = await _render_all_pages(spec, ctx, subsystem_hub)
        population = _component_population(rendered_pages)

        back_ok: bool | None = None
        rerender_ok: bool | None = None
        if spec.navigation.parent is not None:
            parent_id = spec.navigation.parent.name
            back_id = f"{NAV_BACK_ID_PREFIX}{parent_id}"
            back_ok = back_id in population and static_route(back_id) is not None
            if not back_ok:
                report.problems.append(
                    f"{panel_id}: declared parent {parent_id!r} but the "
                    f"{back_id!r} slot is missing or unbound"
                )
            if parent_id in inventory:
                parent_spec = inventory[parent_id]
                first = _component_population(
                    await _render_all_pages(parent_spec, ctx, hubs.get(parent_spec.subsystem)))
                again = _component_population(
                    await _render_all_pages(parent_spec, ctx, hubs.get(parent_spec.subsystem)))
                rerender_ok = first == again
                if not rerender_ok:
                    report.problems.append(
                        f"{panel_id}: parent {parent_id!r} re-render changed "
                        f"its component population (in-place rerender must survive)"
                    )
            else:
                report.problems.append(
                    f"{panel_id}: declared parent {parent_id!r} is not a "
                    f"registered panel"
                )
                rerender_ok = False

        home_ok: bool | None = None
        if spec.navigation.show_home:
            from sb.kernel.panels.registry import resolve_home_hub

            hub = resolve_home_hub(spec, subsystem_hub)
            if hub:
                home_id = f"{NAV_HUB_ID_PREFIX}{hub}"
                home_ok = home_id in population and static_route(home_id) is not None
                if not home_ok:
                    report.problems.append(
                        f"{panel_id}: home hub {hub!r} resolved but the "
                        f"{home_id!r} slot is missing or unbound"
                    )

        report.states[panel_id] = StateReport(
            panel_id=panel_id,
            reachable=is_reachable or panel_id in roots,
            back_ok=back_ok,
            home_ok=home_ok,
            rerender_ok=rerender_ok,
        )
    return report

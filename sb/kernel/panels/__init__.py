"""K8/S9b — the panel/presentation runtime (design-spec §2.3/§2.4/§2.6,
homed in K8's PROVIDES per F-3.4; the canonical plan's D-6 "panel runtime →
K8/S9b").

Layer map:
  sb/spec/panels.py    — the frozen grammar (PanelSpec + children; leaf)
  compile.py           — registration fences (layout coverage, caps, G-10,
                         never-strand, destructive placement, §3.4 rules)
  registry.py          — panel registry + the ONE static custom-id table +
                         hub constants (nav:help / nav:hub:<hub> verbatim)
  router.py            — §3.4 custom-id router (static → g<N>: → expiry)
  context.py           — PanelContext (kernel-constructed; no raw discord)
  render.py            — PanelSpec + PanelContext → RenderedPanel (pure;
                         budget clamping, visible_when, locale seam, nav
                         injection, page-turn)
  engine.py            — open_panel/handle_nav + sessions + invoker lock;
                         presenter PORT (discord adapter materializes)
  browserview.py       — the shared BrowserView engine (sort/filter/page
                         controls for declared Table/List blocks; D-0034)
  selectwindow.py      — the windowed-select engine (a declared
                         ``windowed`` selector pages past Discord's
                         25-option cap with ◀ Prev / Next ▶ nav)
  projections.py       — generated settings panels + help-as-projection

The composition root wires:
  interaction.resolve.install_panel_engine(engine.open_panel)
  engine.install_panel_presenter(<discord adapter presenter>)
  render.install_hub_resolver(<manifest parent_hub lookup>)
"""

from sb.kernel.panels.engine import open_panel  # noqa: F401 — the canonical entry

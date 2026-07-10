"""The UX LAB home panel (band 6 flip) — the shipped ``UxLabHomeView``
(disbot/views/ux_lab/home.py): the 🧪 interface-gallery Home card
(discord.Color.blurple(), the two-paragraph zero-write blurb, the
``Exhibits`` coverage line + the ``How to browse`` field, the plan-doc
footer) over the wing-button rows — 8 exhibit wings + ⚖️ Compare, each
button carrying its emoji as a SEPARATE component field (the shipped
``discord.ui.Button(emoji=...)`` wire shape, unlike general/utility's
in-label emoji). ``parity/goldens/ux_lab/sweep_uxlab.json`` +
``parity/goldens/uxlab/sweep_slash_uxlab.json`` pin every byte.

The shipped view was a timeout-bound session view (``HubView`` family,
author-locked), so ``session_lifecycle=True``: the wing buttons get
run-minted custom_ids (engine ``_mint_ephemeral`` → the Normalizer's
``<cid:N>``), no ``panel_anchors`` row. UNLIKE the general/utility panels
it DID carry the standard nav row — ``nav:help`` + ``nav:hub:admin``
(``↩ Administration``; ux_lab's shipped parent hub is ``admin`` per
disbot/utils/subsystem_registry.py category "admin") — the goldens pin
both literal ids on row 4.

Deliberate under-port notes (parity beyond the goldens):
* the shipped ``Exhibits`` line is registry-derived (``category_counts()``
  over the 64-pattern registry); the wings' exhibit browsers are their own
  slice, so the golden-pinned literal ships here and re-derivation lands
  with the wings;
* the shipped view was author-locked while replying PUBLIC (the slash
  golden pins the no-ephemeral-flag type-4 response) — the grammar couples
  the invoker lock to the ephemeral INVOKER audience, so this ships
  ``Audience.PUBLIC`` (the blackjack shared-view precedent) and the
  author-lock rejoins with the wings slice.
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    TextBlock,
)
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    is_registered,
    panel,
    provider,
)

__all__ = [
    "ensure_panel_refs",
    "install_ux_lab_panels",
    "ux_lab_home_spec",
]

# the shipped Home-card copy (build_home_embed — the goldens pin every byte).
_DESCRIPTION = (
    "Browse every interaction pattern SuperBot could use. Every exhibit "
    "**reacts** when you press it and carries a spec card (use-for / "
    "avoid-for / platform limits).\n\n"
    "**Nothing here is real**: the lab never writes to the database or "
    "changes the server (CI-enforced)."
)

#: the shipped registry coverage line (category_counts() at capture time —
#: 64 registered patterns + the 8 Q-0108–Q-0112 mocks + the 10-probe bench;
#: pinned literal until the wings' exhibit registry ports).
_EXHIBITS = (
    "Buttons **11** · Selects **8** · Modals **6** · Embeds **14** · "
    "Components V2 **8** · PIL cards **6** · Mock studio **9** · "
    "Probe bench **10**"
)

_HOW_TO_BROWSE = (
    "Open a wing → flip exhibits with ◀ ▶ → press things. "
    "🏠 always returns here, in place."
)

#: the shipped footer literal (build_home_embed set_footer) — outside
#: FooterMode's vocabulary, hence the renderer_override below (the
#: utility-panel precedent).
_FOOTER = "Design: docs/planning/ux-lab-interface-gallery-plan-2026-06-12.md"


async def _home_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped Home-card fields (Exhibits + How to browse, verbatim)."""
    del ctx
    return (("Exhibits", _EXHIBITS), ("How to browse", _HOW_TO_BROWSE))


def _wing(action_id: str, label: str, emoji: str, *,
          style: ActionStyle = ActionStyle.PRIMARY) -> PanelActionSpec:
    """One wing button — the shipped separate-emoji wire shape; the wings'
    exhibit browsers port with their own slice, so every click lands on the
    polite pending terminal (the role/utility-band precedent)."""
    return PanelActionSpec(
        action_id=action_id, label=label, emoji=emoji, style=style,
        audience_tier="administrator",       # the shipped admin workbench gate
        handler=HandlerRef(f"ux_lab.{action_id}_wing"))


def ux_lab_home_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="ux_lab.home",
        subsystem="ux_lab",
        title="🧪 UX Lab — interface gallery",
        # the shipped slash reply was PUBLIC (no ephemeral flag —
        # goldens/uxlab pins the bare type-4 data); see the module
        # docstring for the author-lock note.
        audience=Audience.PUBLIC,
        # discord.Color.blurple() — the shipped Home card accent.
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_DESCRIPTION),
              FieldsBlock(provider=ProviderRef("ux_lab.home_fields"))),
        actions=(
            # row 0 — the shipped blurple wing quartet.
            _wing("buttons", "Buttons", "🔘"),
            _wing("selects", "Selects", "📋"),
            _wing("modals", "Modals", "⌨️"),          # ⌨️ (VS16)
            _wing("embeds", "Embeds", "\U0001faa7"),            # 🪧
            # row 1 — the second quartet; the shipped Probe bench was grey.
            _wing("components_v2", "Components V2", "\U0001f9f1"),  # 🧱
            _wing("pil_cards", "PIL cards", "🎨"),
            _wing("mock_studio", "Mock studio", "🎭"),
            _wing("probe_bench", "Probe bench", "🔬",
                  style=ActionStyle.SECONDARY),
            # row 2 — the shipped grey ⚖️ Compare panel.
            _wing("compare", "Compare", "⚖️",         # ⚖️ (VS16)
                  style=ActionStyle.SECONDARY),
        ),
        # the shipped UxLabHomeView carried the standard nav row — 📚 Help
        # (nav:help) + ↩ Administration (nav:hub:admin). home_hub is the
        # rare explicit pin: ux_lab's shipped parent hub is `admin`
        # (subsystem_registry category, verbatim) and no hub resolver is
        # installed until the admin hub's own band ports.
        navigation=NavigationSpec(home_hub="admin"),
        session_lifecycle=True,
        renderer_override=HandlerRef("ux_lab.render_home"),
        justification=(
            "the shipped Home-card footer is the literal plan-doc pointer "
            "'Design: docs/planning/ux-lab-interface-gallery-plan-"
            "2026-06-12.md' — outside FooterMode's none/subsystem/"
            "provenance vocabulary (goldens/ux_lab + goldens/uxlab pin the "
            "byte; the utility-panel precedent). The override delegates to "
            "the grammar renderer and replaces ONLY the footer; body, "
            "fields, actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("buttons", "selects", "modals", "embeds"),
            ("components_v2", "pil_cards", "mock_studio", "probe_bench"),
            ("compare",),
        )),)),
    )


# --- renderer override ------------------------------------------------------------

async def _render_home(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal (see justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered, embed=_dc_replace(rendered.embed, footer=_FOOTER))


# --- registration -----------------------------------------------------------------

def _register_refs() -> None:
    from sb.spec.refs import handler

    if not is_registered(PanelRef("ux_lab.home")):
        panel("ux_lab.home")(ux_lab_home_spec)
    if not is_registered(HandlerRef("ux_lab.render_home")):
        handler("ux_lab.render_home")(_render_home)
    if not is_registered(ProviderRef("ux_lab.home_fields")):
        provider("ux_lab.home_fields")(_home_fields)


_register_refs()


def install_ux_lab_panels() -> tuple[PanelSpec, ...]:
    spec = ux_lab_home_spec()
    try:
        return (register_panel(spec),)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return (spec,)
        raise


def ensure_panel_refs() -> None:
    _register_refs()

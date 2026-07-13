"""Fishing — the 🎣 how-to-fish hub guide port (the completeness-table
2026-07-13 fishing-row residue, #405 claim): the hub's 📖 How to fish
button repoints ``fishing.howtofish_pending`` → the live
``fishing.rules_view`` handler over the NEW fully-static
``fishing.rules_card`` PanelSpec (shipped ``views/fishing/menu.py``
``_rules_embed`` verbatim, sent ephemeral by ``rules_btn`` — the
creature ``rules_card`` precedent, mirrored exactly).
``goldens/fishing/fishing_howtofish_rules_card`` pins the clicked
bytes; ``sweep_fishing`` stays byte-neutral (label/emoji/style
untouched — the Dex-button repoint precedent)."""

from __future__ import annotations


def test_hub_button_repoints_to_the_live_rules_lane():
    from sb.domain.fishing.panels import fishing_hub_spec
    from sb.spec.outcomes import ReplyVisibility
    from sb.spec.refs import HandlerRef

    hub = fishing_hub_spec()
    by_id = {a.action_id: a for a in hub.actions}
    assert by_id["fishing_rules"].handler == HandlerRef("fishing.rules_view")
    # the shipped send was `ephemeral=True` (menu.py rules_btn)
    assert by_id["fishing_rules"].reply_visibility is ReplyVisibility.EPHEMERAL
    # label/emoji/style unchanged — byte-neutral vs sweep_fishing
    assert by_id["fishing_rules"].label == "How to fish"
    assert by_id["fishing_rules"].emoji == "📖"


def test_rules_card_is_the_oracle_embed_verbatim():
    from sb.domain.fishing.panels import RULES_PANEL_ID, rules_card_spec
    from sb.spec.panels import FooterMode, TextBlock

    spec = rules_card_spec()
    assert spec.panel_id == RULES_PANEL_ID == "fishing.rules_card"
    assert spec.title == "📖 How to fish"
    # GAME_COLOR purple (10181046) — _rules_embed color=GAME_COLOR
    assert spec.frame.style_token == "purple"
    assert spec.frame.footer_mode is FooterMode.NONE
    # a fully STATIC card: no override, no actions, no nav
    assert spec.renderer_override is None
    assert spec.actions == ()
    assert spec.navigation.show_help is False
    assert spec.navigation.show_home is False
    # views/fishing/menu.py _rules_embed description, verbatim
    (block,) = spec.body
    assert isinstance(block, TextBlock)
    assert block.text == (
        "**The loop**\n"
        "1. **🎣 Cast** — drop a line, then *wait* for the bite.\n"
        "2. **Bite!** — when the float dips, hit **Reel** before the fish "
        "spits the hook (reel too early and it spooks).\n"
        "3. **Fight** the big ones — keep reeling to land a trophy.\n\n"
        "**Get better catches**\n"
        "• **🎒 Rod** — upgrade your rod for a wider reel window, faster "
        "bites, and less escape.\n"
        "• **🪱 Bait** — load a lure for rarer fish (a consumable knob on "
        "top of your rod).\n"
        "• **⛵ Set sail** — head to deepwater for the rare boat-only "
        "fish.\n"
        "• **📖 Fishdex** — track your collection and personal-best "
        "weights."
    )


def test_rules_card_passes_the_compile_fences():
    from sb.domain.fishing.panels import rules_card_spec
    from sb.kernel.panels.compile import check_panel

    check_panel(rules_card_spec())


def test_manifest_declares_the_card_and_the_pending_is_retired():
    from sb.domain.fishing import service
    from sb.domain.fishing import panels
    from sb.manifest.fishing import MANIFEST
    from sb.spec.refs import HandlerRef, PanelRef, is_registered

    assert "fishing.rules_card" in {p.panel_id for p in MANIFEST.panels}
    panels.ensure_panel_refs()
    service.ensure_handler_refs()
    assert is_registered(PanelRef("fishing.rules_card"))
    assert is_registered(HandlerRef("fishing.rules_view"))
    # the retired hub pending no longer registers (trap 12a) and the
    # deep-system PENDING roster stays empty
    assert not is_registered(HandlerRef("fishing.howtofish_pending"))
    assert service.PENDING == {}

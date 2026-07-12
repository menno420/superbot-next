"""Casino panels (band 6 / parity flip) — the SHIPPED surfaces byte-for-byte:

* ``casino.hub`` — disbot/views/casino/hub.py ``build_casino_hub_panel``:
  the 🎰 Casino embed (GAME_COLOR purple, the two game fields, the shared
  invoker-lock footer), the 🃏 New Poker Table launcher and the DISABLED
  🎡 Roulette (soon) placeholder (the shipped decorator pins
  ``disabled=True`` — outside PanelActionSpec's vocabulary, hence the
  renderer_override), and the shipped standard nav row (📚 Help +
  ↩ Games — ``home_hub="games"`` explicit, the cleanup/ticket
  precedent). ``parity/goldens/casino/sweep_casino.json`` pins every
  byte: run-minted ``<cid:N>`` button ids (timeout session view ⇒
  ``session_lifecycle=True``, no ``panel_anchors`` row), emoji as
  SEPARATE wire fields next to the labels (trap 15a), the literal
  ``nav:help`` / ``nav:hub:games`` slots riding through the mint.

* ``casino.poker_table`` — disbot/views/casino/poker_table.py
  ``_lobby_public_embed`` + ``PokerLobbyView``: the ♠ lobby embed whose
  ``Seated (n/8)`` field and ``Host X starts when ready.`` footer are
  LIVE table state (renderer_override, economy delegation recipe) over
  the four shipped buttons (Join 🪑 success · Leave 🚪 secondary ·
  Start ▶️ primary · Close 🗑️ danger — no nav slots, the shipped
  timeout view). ``parity/goldens/casino/sweep_poker.json`` pins the
  fresh-open bytes (host-only seating, ``👑 AdminActor``).

Trap-24 drift check (casino row): the oracle current-head fragments
(hub.py title/description/fields/buttons; poker_table.py lobby embed,
seat legend, footer, button decorators, constants MAX_SEATS=8 /
START_STACK=1000 / SMALL_BLIND=5 / BIG_BLIND=10) match the corpus
goldens byte-for-byte — NO drift (corpus sha 7f7628e1).
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.outcomes import ReplyVisibility
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
    ProviderRef,
    is_registered,
    panel,
    provider,
)

__all__ = [
    "casino_hub_spec",
    "ensure_panel_refs",
    "install_casino_panels",
    "poker_table_spec",
]

_HUB_FIELDS = "casino.hub_fields"

#: the shipped footer literal (views/casino/hub.py rode the shared
#: author-locked nav view) — outside FooterMode's vocabulary, hence the
#: renderer_override (the community/utility/admin precedent).
_HUB_FOOTER = "Only you can interact with this panel."

# views/casino/hub.py build_casino_hub_embed, verbatim (the golden pins
# every byte).
_HUB_DESCRIPTION = (
    "Group casino games you play together at one table — everyone gets "
    "their **own private, live-updating hand**.\n\n"
    "Pick a game below. Typed shortcut: `!poker`."
)
_HUB_FIELD_ROWS = (
    ("🃏 Texas Hold'em Poker",
     "Multiplayer poker, 2–8 players. Take a seat, get a private hand, "
     "and bet it out — your cards update live as everyone plays. "
     "Play-chips."),
    ("🎡 Roulette",
     "_Coming soon — built on the same shared-table framework._"),
)


def _ensure_hub_fields() -> ProviderRef:
    ref = ProviderRef(_HUB_FIELDS)
    if not is_registered(ref):
        @provider(_HUB_FIELDS)
        async def hub_fields(ctx: object):
            return _HUB_FIELD_ROWS
    return ref


def casino_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="casino.hub",
        subsystem="casino",
        title="🎰 Casino",
        audience=Audience.INVOKER,
        # GAME_COLOR purple (10181046); footer + the disabled placeholder
        # live in the override (see justification).
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        body=(
            TextBlock(_HUB_DESCRIPTION),
            FieldsBlock(provider=_ensure_hub_fields()),
        ),
        actions=(
            PanelActionSpec(
                # K1 claims action_ids bare and repo-global — the casino_
                # prefix keeps the namespace clean (the wire id is
                # run-minted <cid:N> either way).
                action_id="casino_new_poker", label="New Poker Table",
                emoji="🃏", style=ActionStyle.SUCCESS,
                audience_tier="user",
                handler=HandlerRef("casino.poker_open"),
                reply_visibility=ReplyVisibility.EPHEMERAL),
            PanelActionSpec(
                action_id="casino_roulette", label="Roulette (soon)",
                emoji="🎡", style=ActionStyle.SECONDARY,
                audience_tier="user",
                # the shipped callback (unreachable while disabled — the
                # honest twin of the shipped ephemeral notice).
                handler=HandlerRef("casino.roulette_soon"),
                reply_visibility=ReplyVisibility.EPHEMERAL),
        ),
        # the shipped standard nav row: 📚 Help + the hub-named home
        # button "↩ Games" (nav:hub:games — both pinned by the golden);
        # home_hub explicit, the cleanup/ticket precedent (the
        # FOLLOW_PARENT resolver is uninstalled in both roots).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("casino.render_hub"),
        justification=(
            "two shipped surfaces sit outside the grammar's vocabulary "
            "(goldens/casino/sweep_casino pins both): (1) the FOOTER is "
            "the shared invoker-lock literal 'Only you can interact "
            "with this panel.' — outside FooterMode's none/subsystem/"
            "provenance set (the community/utility/admin precedent); "
            "(2) the casino.hub.casino_roulette BUTTON ships "
            "disabled=True (views/casino/hub.py decorator 'Roulette "
            "(soon)') — PanelActionSpec has no disabled field, so the "
            "override sets it per-component by CANONICAL id (§2.9 item-9 "
            "lane; the override runs before the session mint on open AND "
            "before the refresh remap). Title, description, fields, "
            "colors and every other component stay grammar-rendered."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("casino_new_poker", "casino_roulette"),)),)),
    )


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal + the shipped
    disabled Roulette placeholder (see justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    components = tuple(
        _dc_replace(c, disabled=True)
        if c.custom_id == "casino.hub.casino_roulette" else c
        for c in rendered.components)
    return _dc_replace(
        rendered,
        embed=_dc_replace(rendered.embed, footer=_HUB_FOOTER),
        components=components)


# views/casino/poker_table.py _lobby_public_embed description, verbatim
# (constants interpolated at import — the golden pins the bytes).
def _poker_description() -> str:
    from sb.domain.casino.table import (
        BIG_BLIND,
        MAX_SEATS,
        SMALL_BLIND,
        START_STACK,
    )

    return (
        "**Texas Hold'em**, group play. Press **Join** to take a seat — "
        "you'll get a private hand that updates live as everyone "
        "plays.\n\n"
        f"Buy-in: **{START_STACK}** play-chips · Blinds "
        f"{SMALL_BLIND}/{BIG_BLIND} · up to {MAX_SEATS} seats."
    )


def poker_table_spec() -> PanelSpec:
    from sb.domain.casino.table import LOBBY_TIMEOUT

    return PanelSpec(
        panel_id="casino.poker_table",
        subsystem="casino",
        title="♠ Poker Table — open!",
        # the shipped lobby message is PUBLIC in-channel — anyone may
        # take a seat (the view gated per-click, never per-message).
        audience=Audience.PUBLIC,
        timeout_s=LOBBY_TIMEOUT,             # the shipped LOBBY_TIMEOUT=600
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_poker_description()),),
        actions=(
            PanelActionSpec(
                action_id="poker_join", label="Join", emoji="🪑",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("casino.poker_join"),
                reply_visibility=ReplyVisibility.EPHEMERAL),
            PanelActionSpec(
                action_id="poker_leave", label="Leave", emoji="🚪",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("casino.poker_leave"),
                reply_visibility=ReplyVisibility.EPHEMERAL),
            PanelActionSpec(
                action_id="poker_start", label="Start", emoji="▶️",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("casino.poker_start"),
                reply_visibility=ReplyVisibility.EPHEMERAL),
            PanelActionSpec(
                action_id="poker_close", label="Close", emoji="🗑️",
                style=ActionStyle.DANGER, audience_tier="user",
                handler=HandlerRef("casino.poker_close"),
                reply_visibility=ReplyVisibility.EPHEMERAL),
        ),
        # the shipped PokerLobbyView carried ONLY its four buttons (no
        # nav slots; timeout session view) — the golden pins exactly one
        # component row (session-view exemption, the leaderboard/
        # spotlight precedent).
        navigation=NavigationSpec(show_help=False, show_home=False),
        renderer_override=HandlerRef("casino.render_poker_table"),
        justification=(
            "the shipped lobby embed carries LIVE table state on two "
            "named surfaces (goldens/casino/sweep_poker pins the fresh-"
            "open bytes): the 'Seated (n/8)' FIELD interpolates the live "
            "seat count and the 👑-host seat legend, and the FOOTER "
            "interpolates the host's display name ('Host {name} starts "
            "when ready.') — both outside the grammar's static "
            "TextBlock / 2-tuple FieldsBlock vocabulary. The override "
            "delegates to the grammar renderer for every component and "
            "replaces only the embed fields + footer (the economy "
            "delegation recipe); a closed table re-renders the shipped "
            "terminal embed ('♠ Poker Table — closed') with the "
            "teardown reason as its description."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("poker_join", "poker_leave", "poker_start", "poker_close"),
        )),)),
    )


async def _render_poker_table(spec: PanelSpec, ctx) -> object:
    """renderer_override — the lobby's live field/footer over the grammar
    components; ``params['stage'] == 'closed'`` renders the shipped
    teardown terminal (embed only, components withdrawn — the shipped
    ``_teardown`` edit)."""
    from sb.domain.casino.table import MAX_SEATS, get_table
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    rendered = await render_panel(spec, ctx)
    if str(ctx.params.get("stage", "") or "") == "closed":
        reason = str(ctx.params.get("reason", "") or
                     "The host closed the table.")
        embed = RenderedEmbed(
            title="♠ Poker Table — closed", description=reason,
            style_token=spec.frame.style_token)
        return _dc_replace(rendered, embed=embed, components=())
    lobby = get_table(int(ctx.channel_id or 0))
    seated = len(lobby.seats) if lobby else 0
    lines = lobby.seat_lines() if lobby else "—"
    host = lobby.host_name() if lobby else "Player"
    embed = _dc_replace(
        rendered.embed,
        fields=((f"Seated ({seated}/{MAX_SEATS})", lines),),
        footer=f"Host {host} starts when ready.")
    return _dc_replace(rendered, embed=embed)


@panel("casino.hub")
def _hub_factory() -> PanelSpec:
    return casino_hub_spec()


@panel("casino.poker_table")
def _poker_table_factory() -> PanelSpec:
    return poker_table_spec()


def install_casino_panels() -> tuple[PanelSpec, ...]:
    specs = (casino_hub_spec(), poker_table_spec())
    out = []
    for spec in specs:
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def _register_renders() -> None:
    from sb.spec.refs import handler

    if not is_registered(HandlerRef("casino.render_hub")):
        handler("casino.render_hub")(_render_hub)
    if not is_registered(HandlerRef("casino.render_poker_table")):
        handler("casino.render_poker_table")(_render_poker_table)


_register_renders()


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P
    from sb.spec.refs import is_registered as _is
    from sb.spec.refs import panel as _panel

    _ensure_hub_fields()
    _register_renders()
    for pid, factory in (("casino.hub", _hub_factory),
                         ("casino.poker_table", _poker_table_factory)):
        if not _is(_P(pid)):
            _panel(pid)(factory)

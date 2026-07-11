"""The karma result cards (parity flip) — two component-less
session-lifecycle cards over the shipped cogs/karma_cog.py sends:

* ``karma.card`` — the shipped ``_karma_card`` standing embed (magenta
  accent, display-name title, avatar thumbnail, the Karma/Rank/Activity
  field trio, the footer literal) that ``!karma [@user]`` and the
  ephemeral ``/karma`` slash both send.
* ``karma.error_card`` — the shipped ``utils/embeds.error`` red refusal
  envelope (``❌ {message}``, discord.Color.red()) the cog sent for the
  typed grant refusals (self / disabled / cooldown / daily cap).

Both are transient result messages, never refreshable anchored panels
(``session_lifecycle=True`` — the wallet/daily-card precedent); neither
declares a single component, so the sim gate carries zero rows for them
(run-minted session panels are auto-exempt below the floor).
"""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    Audience,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelSpec,
)
from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

__all__ = [
    "CARD_PANEL_ID",
    "ERROR_CARD_PANEL_ID",
    "card_spec",
    "ensure_panel_refs",
    "error_card_spec",
    "install_karma_panels",
]

CARD_PANEL_ID = "karma.card"
ERROR_CARD_PANEL_ID = "karma.error_card"


def card_spec() -> PanelSpec:
    """The shipped karma standing card (cogs/karma_cog.py ``_karma_card``)
    — a component-less per-read result card: the shipped send was a plain
    ``ctx.send(embed=...)`` / ephemeral followup, never an anchored
    panel."""
    return PanelSpec(
        panel_id=CARD_PANEL_ID,
        subsystem="karma",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="magenta", footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("karma.card_render"),
        justification=(
            "the shipped karma card is read-parameterized on every "
            "surface (the target-member title '✨ Karma — {display_name}', "
            "the avatar thumbnail, the INLINE Karma/Rank field pair and "
            "the non-inline Activity field, the footer literal 'Thank "
            "helpful members with !thanks @user' — cogs/karma_cog.py "
            "_karma_card); grammar TextBlocks are static and grammar "
            "fields render non-inline. The card declares no components; "
            "the renderer only composes the embed "
            "(goldens/karma/sweep_karma + karma_slash_card pin the "
            "bytes)."),
        session_lifecycle=True,
    )


def error_card_spec() -> PanelSpec:
    """The shipped red refusal embed (utils/embeds.py ``error``) the karma
    cog sent for every typed grant refusal — a component-less transient
    result message (the shipped send rode ``delete_after=8``; the delete
    tail is the ruled invoking-message-deletion class)."""
    return PanelSpec(
        panel_id=ERROR_CARD_PANEL_ID,
        subsystem="karma",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("karma.error_render"),
        justification=(
            "the shipped refusal is the shared utils/embeds.error "
            "envelope: a bare description embed '❌ {message}' with the "
            "ERROR_COLOR red accent and no title/fields/footer "
            "(goldens/karma/karma_self_grant_rejected + "
            "karma_repeat_cooldown pin the bytes) — the description is "
            "run-parameterized refusal copy, outside the static grammar "
            "TextBlock vocabulary. Zero components; the renderer only "
            "composes the embed."),
        session_lifecycle=True,
    )


async def _member_display(user_id: int, guild_id: int) -> tuple[str, str]:
    """(display name, avatar url) through the guild-directory read port —
    the shipped ``member.display_name`` / ``member.display_avatar.url``
    pair for renderer paths that carry no origin message (the economy
    wallet-card precedent). Degrades to the bare mention + no thumbnail
    when no directory is armed (never invents data)."""
    try:
        from sb.domain.utility.service import guild_directory

        member = await guild_directory().member_info(guild_id, user_id)
    except Exception:  # noqa: BLE001 — no directory ⇒ mention fallback
        return f"<@{user_id}>", ""
    return member.tag.rsplit("#", 1)[0], member.display_avatar_url


async def _render_card(spec: PanelSpec, ctx) -> object:
    """renderer_override — cogs/karma_cog.py ``_karma_card`` verbatim:
    display-name title, magenta accent, avatar thumbnail (skipped when
    the member read degrades — the shipped ``if avatar is not None``
    posture), the Karma/Rank inline pair, the non-inline Activity field,
    the footer literal."""
    from sb.domain.karma import service
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    target = int(params.get("karma_target")
                 or getattr(getattr(ctx, "actor", None), "user_id", 0) or 0)
    record = await service.get_record(guild_id, target)
    name, avatar_url = await _member_display(target, guild_id)
    rank_line = f"#{record.rank}" if record.rank is not None else "unranked"
    embed = RenderedEmbed(
        title=f"✨ Karma — {name}",
        description="",
        fields=(
            ("Karma", f"**{record.points}** ✨", True),
            ("Rank", rank_line, True),
            ("Activity",
             f"received **{record.received_count}** · "
             f"given **{record.given_count}**", False),
        ),
        footer="Thank helpful members with !thanks @user",
        style_token=spec.frame.style_token,
        thumbnail_ref=avatar_url)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_error_card(spec: PanelSpec, ctx) -> object:
    """renderer_override — utils/embeds.py ``error`` verbatim: the
    ``❌ {message}`` description on the red accent, nothing else."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    message = str(params.get("error_text", "") or "")
    embed = RenderedEmbed(
        title="",
        description=f"❌ {message}",
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


@panel(CARD_PANEL_ID)
def _card_factory() -> PanelSpec:
    return card_spec()


@panel(ERROR_CARD_PANEL_ID)
def _error_card_factory() -> PanelSpec:
    return error_card_spec()


handler("karma.card_render")(_render_card)
handler("karma.error_render")(_render_error_card)


def install_karma_panels() -> tuple[PanelSpec, ...]:
    specs = (card_spec(), error_card_spec())
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


def ensure_panel_refs() -> None:
    for pid, factory in ((CARD_PANEL_ID, _card_factory),
                         (ERROR_CARD_PANEL_ID, _error_card_factory)):
        if not is_registered(PanelRef(pid)):
            panel(pid)(factory)
    for hid, fn in (("karma.card_render", _render_card),
                    ("karma.error_render", _render_error_card)):
        if not is_registered(HandlerRef(hid)):
            handler(hid)(fn)

"""The discord materialization of the kernel panel runtime (K8/S9b).

`PanelRuntimeView` is the ONE view class for every grammar-expressible
panel (design-spec §2.3): it is built FROM a kernel `RenderedPanel`, never
hand-assembled per panel. Interaction flow stays kernel-owned — every
component click re-enters through the component adapter → `resolve()`;
this view only enforces the invoker lock pre-dispatch and the
timeout-disable doctrine.

Import-guarded: the module imports cleanly without the discord package
(`PanelRuntimeView`/`build_embed`/`build_view` require it at CALL time).
"""

from __future__ import annotations

import logging

from sb.kernel.panels.engine import may_interact, session_for
from sb.kernel.panels.render import STYLE_TOKEN_COLORS, RenderedPanel

logger = logging.getLogger("sb.adapters.discord.panel_view")

try:  # pragma: no cover — discord is absent in CI containers by design
    import discord
    from discord import ui as discord_ui
except ImportError:  # noqa: SIM105
    discord = None          # type: ignore[assignment]
    discord_ui = None       # type: ignore[assignment]

__all__ = ["DiscordPanelPresenter", "build_embed", "build_files", "build_view"]

_STYLE_MAP = {
    "primary": "primary", "secondary": "secondary", "success": "success",
    "danger": "danger", "link": "link",
}


def _select_option(option):
    """RenderedComponent option → discord.SelectOption: rich mappings carry
    label/value/description/emoji (the shipped shape); plain strings keep the
    compact label==value form."""
    if isinstance(option, dict):
        return discord.SelectOption(
            label=str(option.get("label", "")),
            value=str(option.get("value", option.get("label", ""))),
            description=str(option["description"]) if option.get("description") else None,
            emoji=str(option["emoji"]) if option.get("emoji") else None,
            default=bool(option.get("default", False)))
    return discord.SelectOption(label=str(option), value=str(option))


def build_embed(rendered: RenderedPanel):
    """RenderedEmbed → discord.Embed (budgets already enforced kernel-side).
    Returns None for CONTENT-only panels (RenderedPanel.embed=None)."""
    if discord is None:
        raise RuntimeError("discord is not installed")
    e = rendered.embed
    if e is None:
        return None
    embed = discord.Embed(title=e.title or None, description=e.description or None,
                          color=STYLE_TOKEN_COLORS.get(e.style_token))
    if getattr(e, "author_name", ""):
        embed.set_author(name=e.author_name,
                         icon_url=getattr(e, "author_icon", "") or None)
    for field in e.fields:
        embed.add_field(name=field[0], value=field[1],
                        inline=bool(field[2]) if len(field) > 2 else False)
    if e.footer:
        embed.set_footer(text=e.footer)
    if e.thumbnail_ref:
        embed.set_thumbnail(url=e.thumbnail_ref)
    if getattr(e, "image_url", ""):
        embed.set_image(url=e.image_url)
    if getattr(e, "timestamp", ""):
        # the ISO-8601 string the kernel carries (RenderedEmbed.timestamp) —
        # the parity twin serializes it verbatim; here it becomes the native
        # datetime discord.py stamps on the wire.
        import datetime as _dt

        try:
            embed.timestamp = _dt.datetime.fromisoformat(e.timestamp)
        except ValueError:
            pass  # a malformed stamp degrades to no timestamp, never a crash
    return embed


def build_files(rendered: RenderedPanel):
    """RenderedAttachment tuple → discord.File list (the shipped card sends,
    e.g. the /myprofile ``profile.png`` hero card)."""
    if discord is None:
        raise RuntimeError("discord is not installed")
    import io

    return [discord.File(io.BytesIO(a.data), filename=a.filename)
            for a in getattr(rendered, "attachments", ()) or ()]


def build_view(rendered: RenderedPanel):
    """RenderedPanel → the ONE PanelRuntimeView."""
    if discord_ui is None:
        raise RuntimeError("discord is not installed")

    class PanelRuntimeView(discord_ui.View):
        """Invoker-lock + timeout-disable over kernel-rendered components.
        Every child click dispatches through the registered component
        adapter (custom_id → router → resolve()) — no callbacks here."""

        def __init__(self) -> None:
            super().__init__(timeout=rendered.timeout_s)
            self.panel_id = rendered.panel_id
            self.message = None     # set by the presenter after send
            for comp in rendered.components:
                if comp.kind == "selector" and getattr(comp, "native_picker",
                                                       "") == "role":
                    # Discord-native role picker (wire type 6) — the
                    # shipped ticket setup staff-role picker shape.
                    item = discord_ui.RoleSelect(
                        custom_id=comp.custom_id,
                        placeholder=comp.placeholder or None,
                        min_values=comp.min_values, max_values=comp.max_values,
                        row=comp.row)
                elif comp.kind == "selector" and getattr(comp, "channel_types",
                                                         None):
                    # Discord-native channel picker (wire type 8) — the
                    # shipped LogChannelSelectView shape.
                    item = discord_ui.ChannelSelect(
                        custom_id=comp.custom_id,
                        placeholder=comp.placeholder or None,
                        min_values=comp.min_values, max_values=comp.max_values,
                        channel_types=[discord.ChannelType(t)
                                       for t in comp.channel_types],
                        row=comp.row)
                elif comp.kind == "selector":
                    item = discord_ui.Select(
                        custom_id=comp.custom_id, placeholder=comp.placeholder or None,
                        min_values=comp.min_values, max_values=comp.max_values,
                        # an empty provider roster renders DISABLED with its
                        # empty_state placeholder (the kernel already set
                        # comp.disabled — codex P3 on the pickers PR: the
                        # live materializer dropped the flag, so the "—"
                        # filler option was clickable).
                        disabled=bool(getattr(comp, "disabled", False)),
                        options=[_select_option(o) for o in comp.options] or
                                [discord.SelectOption(label="—", value="")],
                        row=comp.row)
                else:
                    item = discord_ui.Button(
                        custom_id=comp.custom_id, label=comp.label or None,
                        emoji=comp.emoji or None, disabled=comp.disabled,
                        style=getattr(discord.ButtonStyle, _STYLE_MAP.get(
                            comp.style, "secondary")),
                        row=comp.row)
                self.add_item(item)

        async def interaction_check(self, interaction) -> bool:
            key = str(getattr(getattr(interaction, "message", None), "id", ""))
            session = session_for(key)
            user_id = getattr(getattr(interaction, "user", None), "id", None)
            if not may_interact(session, user_id):
                try:
                    await interaction.response.send_message(
                        "This panel belongs to someone else — open your own.",
                        ephemeral=True)
                except Exception:  # noqa: BLE001
                    logger.debug("invoker-lock notice failed", exc_info=True)
                return False
            return True

        async def on_timeout(self) -> None:
            for child in self.children:
                child.disabled = True
            if self.message is not None:
                try:
                    await self.message.edit(view=self)
                except Exception:  # noqa: BLE001 — timeout-disable is best-effort
                    logger.debug("timeout-disable edit failed", exc_info=True)

    return PanelRuntimeView()


class DiscordPanelPresenter:
    """The engine's presenter port, discord-side: send (or edit, for
    page-turns/nav on component surfaces) the rendered panel; returns the
    message id as the engine's opaque session key."""

    async def __call__(self, rendered: RenderedPanel, req) -> object:
        embed = build_embed(rendered)
        view = build_view(rendered)
        origin = req.origin
        interaction_response = getattr(origin, "response", None)
        ephemeral = rendered.audience == "invoker"
        message = None
        if getattr(rendered, "edit_message_ref", None) is not None:
            # session-view refresh: deferred-update ack, then edit the
            # ORIGINAL message in place (the shipped safe_defer + safe_edit
            # loop of the game views).
            if interaction_response is not None and not interaction_response.is_done():
                await interaction_response.defer()
            message = getattr(origin, "message", None)
            if message is not None:
                await message.edit(embed=embed, view=view)
                view.message = message
            return rendered.edit_message_ref
        file_kwargs = {}
        files = build_files(rendered)
        if files:
            file_kwargs["files"] = files
        if getattr(rendered, "content", None) is not None:
            # CONTENT-only (or content-bearing) panel message — the shipped
            # plain-text send carrying a component View.
            file_kwargs["content"] = rendered.content
        if (rendered.anchor_policy == "channel_anchor"
                and getattr(origin, "channel", None) is not None):
            # CHANNEL_ANCHOR: always a fresh channel message, even when a
            # component click drives the open (tournament round views) — an
            # already-acked interaction must not edit its original response.
            message = await origin.channel.send(embed=embed, view=view,
                                                **file_kwargs)
        elif interaction_response is not None and not interaction_response.is_done():
            await interaction_response.send_message(
                embed=embed, view=view, ephemeral=ephemeral, **file_kwargs)
            message = await origin.original_response()
        elif getattr(origin, "followup", None) is not None:
            # already-acked interaction (resolve()'s AUTO defer): the panel
            # rides a webhook FOLLOWUP send, never a PATCH of the deferred
            # original — the shipped safe_defer + safe_followup split the
            # parity twin mirrors (transport.py: first response
            # `interaction_response`, every later one `followup_send`;
            # goldens/karma/karma_slash_card.json pins the wire shape).
            message = await origin.followup.send(
                embed=embed, view=view, ephemeral=ephemeral, **file_kwargs)
        elif hasattr(origin, "reply"):
            message = await origin.reply(embed=embed, view=view, **file_kwargs)
        view.message = message
        for emoji in (getattr(rendered, "self_reactions", ()) or ()
                      if message is not None else ()):
            # the shipped `reg_msg.add_reaction("✅")` primer — best-effort
            # (a missing add-reactions permission never takes the panel down).
            try:
                await message.add_reaction(emoji)
            except Exception:  # noqa: BLE001
                logger.warning("self-reaction %r failed on %s", emoji,
                               rendered.panel_id, exc_info=True)
        return getattr(message, "id", None)

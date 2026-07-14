"""The WORKSPACE-NOTICE ride (ORDER 019 item 5b, half 2), ported from the
oracle (menno420/superbot @bbc524e4, ``disbot/views/setup/_anchor.py``
``push_setup_notice``):

    Append a one-shot durable notice into the workspace channel.
    Resolves the workspace channel only — does not touch the anchor
    message id. Used for event records (e.g. "Apply Recommended
    succeeded", "section X failed") that must not overwrite canonical
    state. Returns ``True`` on success, ``False`` on any failure.

The oracle's deliberate split — ``render_setup_state`` (anchor
REPLACEMENT) vs ``push_setup_notice`` (event APPEND) — survives here:
the anchor lanes ride ``setup.open_workspace`` / the resume sweep's
``edit_anchored_panel``; THIS lane only ever ``channel.send``s a fresh
embed (``service.post_panel_to_channel``, the ``/setup-status`` durable-
notice precedent) and never reads or writes ``setup_message_id``.

Kernel-idiom divergences, ledgered (the essential_steps.py adaptation
doctrine — same semantics, only the seams differ):

* the oracle took a ``discord.Guild`` + a prebuilt ``discord.Embed``;
  this lane takes the driving request + title/description/style and
  composes the embed in the ``setup.workspace_notice`` panel's renderer
  (the status-card precedent — a component-less durable notice panel);
* the oracle resolved the channel via ``setup_channel.
  ensure_setup_channel(guild, existing_channel_id=session…)``; the
  target's ``service.ensure_setup_channel`` carries the same
  find-or-create semantics over the channel-domain ports;
* the never-raises contract is the oracle's own: any failure logs at
  WARNING/exception level and answers ``False`` — callers decide the
  ephemeral fallback (``setup_cog.setup_status_slash``'s posture).

NO GOLDEN drives a notice push (the panels.py module pin) — the oracle
sources pin the semantics.
"""

from __future__ import annotations

import logging

__all__ = [
    "NOTICE_PANEL_ID",
    "ensure_setup_notice_refs",
    "push_setup_notice",
    "workspace_notice_spec",
]

logger = logging.getLogger("sb.domain.setup")

NOTICE_PANEL_ID = "setup.workspace_notice"


def workspace_notice_spec():
    """The one-shot durable notice card — component-less (the
    ``setup.status_card`` precedent: never anchored, never refreshed);
    title/description/accent arrive per-post as params."""
    from sb.spec.panels import (
        Audience, EmbedFrameSpec, FooterMode, LayoutSpec, NavigationSpec,
        PageSpec, PanelSpec,
    )
    from sb.spec.refs import HandlerRef

    return PanelSpec(
        panel_id=NOTICE_PANEL_ID,
        subsystem="setup",
        title="🛰 Setup notice",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="green", footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("setup.workspace_notice_render"),
        justification=(
            "the shipped notices are per-event embeds built at the push "
            "site (wizard._on_apply_recommended's '✅ Recommended staged' "
            "record, hub's '⚠️ Section failed' record — "
            "views/setup/_anchor.push_setup_notice took a prebuilt "
            "discord.Embed); title, description and accent are "
            "post-parameterized, outside the static grammar vocabulary. "
            "Zero components; the renderer only composes the embed (no "
            "golden pins a notice — the oracle source does)."),
        session_lifecycle=True,
    )


async def _render_workspace_notice(spec, ctx) -> object:
    """renderer_override — the pushed embed verbatim from the post
    params (the oracle passed the built ``discord.Embed`` through)."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    embed = RenderedEmbed(
        title=str(params.get("notice_title") or spec.title),
        description=str(params.get("notice_description") or ""),
        style_token=str(params.get("notice_style")
                        or spec.frame.style_token))
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def push_setup_notice(req, *, title: str, description: str,
                            style_token: str = "green") -> bool:
    """Append a one-shot durable notice into the workspace channel (the
    oracle ``push_setup_notice`` contract): resolve-or-create the
    workspace, ``channel.send`` the embed, NEVER touch the anchor id.
    Returns ``True`` on success, ``False`` on any failure — never
    raises (callers surface their own ephemeral fallback)."""
    from sb.domain.setup import service

    try:
        guild_id = int(req.guild_id or 0)
        invoker = int(getattr(req.actor, "user_id", 0) or 0)
        channel_id, _created = await service.ensure_setup_channel(
            guild_id, invoker)
        message_id = await service.post_panel_to_channel(
            NOTICE_PANEL_ID, req, channel_id,
            params={"notice_title": title,
                    "notice_description": description,
                    "notice_style": style_token})
    except Exception:  # noqa: BLE001 — the oracle never-raises contract
        logger.warning("push_setup_notice: send failed (guild=%s)",
                       getattr(req, "guild_id", None), exc_info=True)
        return False
    return message_id is not None


# --- registration ------------------------------------------------------------------------

def _register_notice_panel() -> None:
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    if not is_registered(HandlerRef("setup.workspace_notice_render")):
        handler("setup.workspace_notice_render")(_render_workspace_notice)
    if not is_registered(PanelRef(NOTICE_PANEL_ID)):
        panel(NOTICE_PANEL_ID)(workspace_notice_spec)


_register_notice_panel()


def ensure_setup_notice_refs() -> None:
    _register_notice_panel()

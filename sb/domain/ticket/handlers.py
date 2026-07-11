"""Ticket handlers + the `!ticket` hub panel (band-8 parity slice) — the
shipped cogs/ticket_cog.py command family and views/tickets/hub.py
TicketHubView as declared grammar, at the v1 (config-absent) schema epoch
(see sb/domain/ticket/service.py for the under-port boundary)."""

from __future__ import annotations

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["Reply", "ensure_handler_refs", "ensure_panel_refs",
           "install_ticket_panels", "ticket_hub_spec"]

#: shipped guard bytes, verbatim (cogs/ticket_cog.py) — each pinned by its
#: golden (goldens/ticket/sweep_ticket_new / _add / _remove / _claim /
#: _close).
_USAGE_NEW = "Describe your issue: `!ticket new <subject>`."
_NOT_TICKET_CHANNEL = "This isn't an open ticket channel."

#: shipped hub copy (views/tickets/hub.py _build_hub_embed's
#: not-set-up branch, verbatim) — goldens/ticket/sweep_ticket.json pins
#: both lines.
_HUB_NOT_SET_UP = (
    "The ticket system isn't set up yet.\n"
    "An admin can run **`!ticketsetup @StaffRole`** to enable it."
)

#: shipped empty-state reply of the hub's "My open tickets" button
#: (views/tickets/hub.py list_user_open → empty), verbatim.
_NO_OPEN_TICKETS = "You have no open tickets."


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("ticket.new")):
        return

    @handler("ticket.new")
    async def ticket_new(req) -> Reply:
        """`!ticket new <subject>` — the shipped ticket_new lane
        (aliases open/create). Shipped order verbatim: the empty-subject
        usage guard FIRST (goldens/ticket/sweep_ticket_new pins the byte),
        then ticket_mutation.open_ticket's eligibility check — which, at
        the v1 config-absent epoch, always answers the shipped
        REASON_NOT_CONFIGURED refusal (the channel-provisioning open flow
        lands with the ticket-mutation slice)."""
        from sb.domain.ticket import service

        argv = tuple(req.args.get("argv", ()) or ())
        subject = " ".join(str(t) for t in argv).strip()
        if not subject:
            return Reply(BLOCKED, _USAGE_NEW)
        # the shipped open flow's eligibility check runs before any effect
        # (ticket_mutation.open_ticket); at the v1 config-absent epoch it
        # always refuses — the configured open flow (channel provisioning
        # + ticket row) is the ticket-mutation slice's port.
        await service.get_config(int(req.guild_id or 0))
        return Reply(BLOCKED, service.NOT_CONFIGURED_MSG)

    async def _require_open_ticket(req) -> Reply | None:
        """The shipped in-channel guard every manage lane runs FIRST
        (cogs/ticket_cog.py: ``ticket is None or ticket.get("status") !=
        "open"``). The shipped staff/opener authority re-checks sit AFTER
        this guard (they need the ticket row) — they land with the
        ticket-mutation slice."""
        from sb.domain.ticket import service

        ticket = await service.get_ticket_for_channel(
            int(req.channel_id or 0))
        if ticket is None or ticket.get("status") != "open":
            return Reply(BLOCKED, _NOT_TICKET_CHANNEL)
        return None

    @handler("ticket.add")
    async def ticket_add(req) -> Reply:
        """`!ticket add @member` — goldens/ticket/sweep_ticket_add pins
        the non-ticket-channel guard byte."""
        guard = await _require_open_ticket(req)
        if guard is not None:
            return guard
        # an open ticket resolved — the shipped manage body (the staff/
        # opener authority re-check + the mutation) is the ticket-mutation
        # slice's port; unreachable at the v1 epoch (no ticket rows).
        return Reply(BLOCKED, _NOT_TICKET_CHANNEL)

    @handler("ticket.remove")
    async def ticket_remove(req) -> Reply:
        """`!ticket remove @member` — goldens/ticket/sweep_ticket_remove
        pins the guard byte."""
        guard = await _require_open_ticket(req)
        if guard is not None:
            return guard
        # an open ticket resolved — the shipped manage body (the staff/
        # opener authority re-check + the mutation) is the ticket-mutation
        # slice's port; unreachable at the v1 epoch (no ticket rows).
        return Reply(BLOCKED, _NOT_TICKET_CHANNEL)

    @handler("ticket.claim")
    async def ticket_claim(req) -> Reply:
        """`!ticket claim` — goldens/ticket/sweep_ticket_claim pins the
        guard byte."""
        guard = await _require_open_ticket(req)
        if guard is not None:
            return guard
        # an open ticket resolved — the shipped manage body (the staff/
        # opener authority re-check + the mutation) is the ticket-mutation
        # slice's port; unreachable at the v1 epoch (no ticket rows).
        return Reply(BLOCKED, _NOT_TICKET_CHANNEL)

    @handler("ticket.close")
    async def ticket_close(req) -> Reply:
        """`!ticket close [reason]` — goldens/ticket/sweep_ticket_close
        pins the guard byte."""
        guard = await _require_open_ticket(req)
        if guard is not None:
            return guard
        # an open ticket resolved — the shipped manage body (the staff/
        # opener authority re-check + the mutation) is the ticket-mutation
        # slice's port; unreachable at the v1 epoch (no ticket rows).
        return Reply(BLOCKED, _NOT_TICKET_CHANNEL)

    @handler("ticket.open_submit")
    async def ticket_open_submit(req) -> Reply:
        """The hub's "Open a ticket" modal SUBMIT (shipped: TicketOpenModal
        → ticket_mutation.open_ticket, eligibility first). At the v1
        config-absent epoch every submit answers the shipped
        REASON_NOT_CONFIGURED refusal — the provisioning flow is the
        ticket-mutation slice's port."""
        from sb.domain.ticket import service

        await service.get_config(int(req.guild_id or 0))
        return Reply(BLOCKED, service.NOT_CONFIGURED_MSG)

    @handler("ticket.my_tickets")
    async def ticket_my_tickets(req) -> Reply:
        """The hub's "My open tickets" button (views/tickets/hub.py):
        list_user_open, empty → the shipped empty-state byte."""
        from sb.domain.ticket import service

        mine = await service.list_user_open(
            int(req.guild_id or 0), int(req.actor.user_id or 0))
        if not mine:
            return Reply(BLOCKED, _NO_OPEN_TICKETS)
        # a ticket list resolved — the shipped per-ticket channel-link
        # lines are the ticket-mutation slice's port; unreachable at the
        # v1 epoch (no ticket rows).
        return Reply(SUCCESS, _NO_OPEN_TICKETS)

    @handler("ticket.post_panel")
    async def ticket_post_panel(req) -> Reply:
        """The hub's "Post panel here" button. Shipped: a staff check,
        then post_launcher(channel) — the persistent public launcher panel
        (views/tickets/launcher.py, static custom_id
        "ticket:launcher:open"). The launcher panel is the ticket-mutation
        slice's port (its only useful lane is the modal→open flow); at the
        v1 config-absent epoch this answers the shipped open-lane
        REASON_NOT_CONFIGURED refusal instead of posting a dead launcher
        (under-port note; unpinned surface — no golden carries the
        click)."""
        from sb.domain.ticket import service

        await service.get_config(int(req.guild_id or 0))
        return Reply(BLOCKED, service.NOT_CONFIGURED_MSG)


# --- panel ------------------------------------------------------------------------

def ticket_hub_spec():
    from sb.spec.panels import (
        ActionStyle,
        Audience,
        EmbedFrameSpec,
        FooterMode,
        LayoutSpec,
        ModalFieldSpec,
        ModalSpec,
        NavigationSpec,
        PageSpec,
        PanelActionSpec,
        PanelSpec,
    )
    from sb.spec.outcomes import DeferMode
    from sb.spec.refs import HandlerRef

    return PanelSpec(
        panel_id="ticket.hub",
        subsystem="ticket",
        # the shipped hub embed (views/tickets/hub.py _build_hub_embed):
        # title + blurple accent — goldens/ticket/sweep_ticket.json pins
        # both bytes (color 5793266 = discord.Color.blurple(), the
        # STYLE_TOKEN_COLORS entry the UX Lab home minted).
        title="🎫 Support tickets",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        # no declared body: the shipped description is STATE-dependent
        # (cfg branch) — the renderer_override below supplies it (see
        # justification).
        actions=(
            # the shipped TicketHubView buttons verbatim — label + emoji
            # as SEPARATE wire fields (@discord.ui.button(label=...,
            # emoji=...); the golden pins {"emoji": {"id": null, "name":
            # "🎫"}} next to the label, unlike the glyph-in-label panels).
            PanelActionSpec(
                action_id="open_ticket", label="Open a ticket",
                emoji="🎫", style=ActionStyle.PRIMARY,
                audience_tier="user",
                # the shipped click opened TicketOpenModal (send_modal) —
                # G-10: the form issues on open, the handler runs on
                # submit (the proof_channel grant posture).
                defer_mode=DeferMode.MODAL,
                handler=HandlerRef("ticket.open_submit"),
                modal=ModalSpec(
                    modal_id="ticket.open_form",
                    # the shipped modal title (views/tickets/_shared.py
                    # TicketOpenModal, verbatim).
                    title="Open a support ticket",
                    fields=(ModalFieldSpec(field_id="subject",
                                           label="Subject",
                                           required=True),)),
            ),
            PanelActionSpec(
                action_id="my_tickets", label="My open tickets",
                emoji="📋", style=ActionStyle.SECONDARY,
                audience_tier="user",
                handler=HandlerRef("ticket.my_tickets")),
            PanelActionSpec(
                action_id="post_panel", label="Post panel here",
                emoji="📮", style=ActionStyle.SECONDARY,
                audience_tier="user",
                handler=HandlerRef("ticket.post_panel")),
        ),
        # the shipped hub carried the standard nav row — the golden pins
        # nav:help ("📚 Help") + nav:hub:community ("↩ Community"); the
        # explicit home_hub pin is the cleanup-hub precedent (the shipped
        # parent_hub assignment, subsystem_registry.py verbatim — the same
        # mapping sb/domain/help/categories.py _PARENT_HUB carries).
        navigation=NavigationSpec(home_hub="community"),
        # the shipped TicketHubView is a ctx-bound timeout view
        # (ticket_cog.ticket: `view.message = await ctx.send(...)`) —
        # session lifecycle: run-minted ids (<cid:1>..<cid:3>), never in
        # panel_anchors (the golden pins the no-anchor-row delta).
        session_lifecycle=True,
        renderer_override=HandlerRef("ticket.render_hub"),
        justification=(
            "the shipped hub embed's description is STATE-dependent "
            "(views/tickets/hub.py _build_hub_embed: the not-set-up copy "
            "when `cfg is None or not cfg.is_set_up`, the configured "
            "body otherwise) — outside the grammar's static-TextBlock "
            "vocabulary; goldens/ticket/sweep_ticket.json pins the "
            "not-set-up bytes (the proof_channel-hub precedent). The "
            "override delegates to the grammar renderer and adjusts ONLY "
            "the description; actions, layout, frame and nav stay "
            "declared. The configured-branch body is unpinned (no golden "
            "captures a set-up guild — the config store is the "
            "ticket-mutation slice's port) and lands with that slice "
            "(under-port note)."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            # the shipped single button row, order verbatim.
            ("open_ticket", "my_tickets", "post_panel"),
        )),)),
    )


async def _render_hub(spec, ctx) -> object:
    """Grammar render + the ONE shipped adjustment (see the spec's
    justification): the state-dependent description."""
    from dataclasses import replace as _dc_replace

    from sb.domain.ticket import service
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    # the shipped branch test verbatim (`cfg is None or not cfg.is_set_up`
    # ⇒ the not-set-up copy). The configured branch's body is unpinned and
    # lands with the ticket-mutation slice (see the spec's justification);
    # at the v1 epoch cfg is always None (service module docstring), so
    # this renders the exact state goldens/ticket/sweep_ticket captured.
    await service.get_config(gid)
    description = _HUB_NOT_SET_UP
    return _dc_replace(
        rendered, embed=_dc_replace(rendered.embed, description=description))


def install_ticket_panels():
    from sb.kernel.panels.registry import register_panel

    spec = ticket_hub_spec()
    try:
        return (register_panel(spec),)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return (spec,)
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    if not is_registered(PanelRef("ticket.hub")):
        @panel("ticket.hub")
        def _factory():
            return ticket_hub_spec()
    if not is_registered(HandlerRef("ticket.render_hub")):
        handler("ticket.render_hub")(_render_hub)


def ensure_handler_refs() -> None:
    _register()


_register()
ensure_panel_refs()

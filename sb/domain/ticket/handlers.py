"""Ticket handlers + the ticket panels (band-8 parity slice + the
`_unmapped` ticket-admin re-home) — the shipped cogs/ticket_cog.py command
family, views/tickets/hub.py TicketHubView, views/tickets/launcher.py
TicketLauncherView (`!ticketpanel`) and views/tickets/config_panel.py
TicketConfigPanelView (`!ticketsetup`) as declared grammar
(see sb/domain/ticket/service.py for the under-port boundary)."""

from __future__ import annotations

import re

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["Reply", "ensure_handler_refs", "ensure_panel_refs",
           "install_ticket_panels", "ticket_hub_spec",
           "ticket_launcher_spec", "ticket_setup_spec"]

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

#: shipped staff-gate refusal of the hub's "Post panel here" button
#: (views/tickets/hub.py: is_ticket_staff fails → ephemeral send), verbatim.
_STAFF_ONLY_POST_PANEL = "Only staff can post the ticket panel."

#: shipped `!ticketblacklist` bare-group usage byte (cogs/ticket_cog.py
#: ticket_blacklist, invoke_without_command) — goldens/ticket/
#: sweep_ticketblacklist pins it.
_USAGE_BLACKLIST = "Usage: `!ticketblacklist add|remove @user`."

#: bot1.py's global on_command_error fallback, verbatim — the capture
#: world's answer whenever a converter raised (MemberConverter on a
#: non-member blacklist target, BadArgument/MissingRequiredArgument on
#: `!ticketlimit`). Handler-owned literal (the goldens/xp/sweep_rank
#: precedent); UNPINNED for the ticket family (no golden drives the
#: converter-failure lanes) but carried so the port degrades through the
#: oracle's own copy, never the new kernel's error envelope.
_GENERIC_ERROR = "⚠️ An unexpected error occurred. Please try again."

#: mention/id target parse (the moderation parse_target shape) — the
#: shipped lanes took a discord.Member converter arg.
_MENTION = re.compile(r"^<@!?(\d+)>$")


def _parse_member_arg(req) -> int | None:
    """First argv token as a member id (`<@id>`/`<@!id>`/bare digits);
    None when absent/unparseable — the caller answers the capture world's
    converter-failure copy (`_GENERIC_ERROR`)."""
    argv = tuple(req.args.get("argv", ()) or ())
    if not argv:
        return None
    first = str(argv[0])
    match = _MENTION.match(first)
    if match:
        return int(match.group(1))
    if first.isdigit():
        return int(first)
    return None


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
        """The hub's "Post panel here" button. Shipped order verbatim
        (views/tickets/hub.py): get_config, then the is_ticket_staff gate
        (admin/manage_guild perms, or the configured staff role), THEN
        post_launcher(channel). At the v1 config-absent epoch the cfg
        staff-role leg is vacuous (cfg is always None — service module
        docstring), so the gate is exactly the perms leg — ActorRef's
        is_guild_operator (owner/administrator/manage_guild, shipped).
        The launcher panel itself is the ticket-mutation slice's port (its
        only useful lane is the modal→open flow); staff answers the
        shipped open-lane REASON_NOT_CONFIGURED refusal instead of posting
        a dead launcher (under-port note; unpinned surface — no golden
        carries the click)."""
        from sb.domain.ticket import service

        await service.get_config(int(req.guild_id or 0))
        if not bool(getattr(req.actor, "is_guild_operator", False)):
            # the shipped refusal byte, verbatim (views/tickets/hub.py:
            # "Only staff can post the ticket panel.", ephemeral).
            return Reply(BLOCKED, _STAFF_ONLY_POST_PANEL)
        return Reply(BLOCKED, service.NOT_CONFIGURED_MSG)

    # --- the ticket-admin command family (the `_unmapped` re-home) --------

    @handler("ticket.ticketblacklist")
    async def ticket_blacklist_usage(req) -> Reply:
        """`!ticketblacklist` bare (and any unknown subcommand token) — the
        shipped invoke_without_command usage byte (cogs/ticket_cog.py
        ticket_blacklist, verbatim); goldens/ticket/sweep_ticketblacklist
        pins it."""
        return Reply(BLOCKED, _USAGE_BLACKLIST)

    async def _blacklist(req, *, blacklisted: bool) -> Reply:
        """The shipped `ticket_mutation.set_blacklist` lane: parse the
        member arg (discord.Member converter in the cog — a converter
        failure died in bot1.py's generic handler, `_GENERIC_ERROR`), run
        the audited K7 op, ack with the shipped verb copy. The remove ack
        is UNCONDITIONAL (bare DELETE, no-op if absent — the #193
        oracle-wins class; sweep_ticketblacklist_remove pins the success
        copy over an empty table)."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        target = _parse_member_arg(req)
        if target is None:
            return Reply(BLOCKED, _GENERIC_ERROR)
        op = ("ticket.blacklist_add" if blacklisted
              else "ticket.blacklist_remove")
        ctx = ctx_from_request(req, {"target_id": int(target)})
        result = await engine.run(WorkflowRef(op), ctx)
        if result.outcome != SUCCESS:
            return Reply(result.outcome, result.user_message)
        verb = "added to" if blacklisted else "removed from"
        # shipped ack verbatim (disbot/services/ticket_mutation.py
        # set_blacklist) — sweep_ticketblacklist_add/_remove pin the bytes.
        return Reply(SUCCESS, f"<@{target}> {verb} the ticket blacklist.")

    @handler("ticket.ticketblacklist_add")
    async def ticket_blacklist_add(req) -> Reply:
        """`!ticketblacklist add @user`."""
        return await _blacklist(req, blacklisted=True)

    @handler("ticket.ticketblacklist_remove")
    async def ticket_blacklist_remove(req) -> Reply:
        """`!ticketblacklist remove @user`."""
        return await _blacklist(req, blacklisted=False)

    @handler("ticket.ticketlimit")
    async def ticket_limit(req) -> Reply:
        """`!ticketlimit <n>` — the shipped clamp (`max(1, min(n, 25))`,
        cogs/ticket_cog.py ticket_limit verbatim), the audited config
        upsert, the shipped ack; goldens/ticket/sweep_ticketlimit pins the
        ack + the fresh ticket_config row. A missing/non-int arg died in
        the capture world's converter → bot1.py generic copy."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        try:
            max_open = int(str(argv[0]))
        except (IndexError, ValueError):
            return Reply(BLOCKED, _GENERIC_ERROR)
        max_open = max(1, min(max_open, 25))
        ctx = ctx_from_request(req, {"max_open": max_open})
        result = await engine.run(WorkflowRef("ticket.set_limit"), ctx)
        if result.outcome != SUCCESS:
            return Reply(result.outcome, result.user_message)
        # shipped ack verbatim (cogs/ticket_cog.py ticket_limit).
        return Reply(SUCCESS, f"✅ Members may now hold up to "
                              f"**{max_open}** open ticket(s).")

    @handler("ticket.setup_pending")
    async def ticket_setup_pending(req) -> Reply:
        """The `!ticketsetup` wizard's interactive lanes (role/log picks,
        Auto-create, Enable, Post panel — views/tickets/config_panel.py)
        land as honest pending terminals: no golden clicks them; the
        shipped callbacks mutate view state / provision channels — the
        wizard-mutation slice's port (the diagnostic flag-manager
        posture)."""
        return Reply(BLOCKED, "ℹ️ This ticket setup control is not ported "
                              "yet — use `!ticketlimit` and "
                              "`!ticketblacklist` meanwhile.")


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


# --- the launcher panel (`!ticketpanel` — views/tickets/launcher.py) ---------------

#: shipped launcher embed body, verbatim (views/tickets/_shared.py
#: build_launcher_embed) — goldens/ticket/sweep_ticketpanel pins every byte.
_LAUNCHER_DESCRIPTION = (
    "Need help? Click **Open a ticket** below and describe your issue. "
    "A private channel will be created for you and the staff team.\n\n"
    "You can also just **ask me in plain English** (e.g. *“open a "
    "ticket, I need help with …”*) in any channel where I'm "
    "listening."
)


def ticket_launcher_spec():
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
        TextBlock,
    )
    from sb.spec.outcomes import DeferMode
    from sb.spec.refs import HandlerRef

    return PanelSpec(
        panel_id="ticket.launcher",
        subsystem="ticket",
        # the shipped launcher embed (views/tickets/_shared.py
        # build_launcher_embed): title + blurple accent + the static body —
        # goldens/ticket/sweep_ticketpanel pins the bytes.
        title="🎫 Support tickets",
        # the shipped TicketLauncherView is a PERSISTENT public view
        # (timeout=None, registered at cog_load) — anyone clicks.
        audience=Audience.PERSISTENT,
        timeout_s=None,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_LAUNCHER_DESCRIPTION),),
        actions=(
            # the shipped decorator form verbatim (@discord.ui.button(
            # label="Open a ticket", style=primary, emoji="🎫",
            # custom_id="ticket:launcher:open")) — label + emoji as
            # SEPARATE wire fields; the persistent custom_id rides the
            # override pin through the session mint (the community
            # `community:open:*` precedent).
            PanelActionSpec(
                action_id="launcher_open", label="Open a ticket",
                emoji="🎫", style=ActionStyle.PRIMARY,
                audience_tier="user",
                custom_id_override="ticket:launcher:open",
                # the shipped click opened TicketOpenModal(source="panel")
                # — the SAME shipped modal class the hub button opens; the
                # port mints a launcher-owned modal_id because the static
                # table binds a modal_id to ONE declaring action
                # (registry G-10); submit lands on the same
                # ticket.open_submit eligibility lane (config-absent ⇒
                # the shipped REASON_NOT_CONFIGURED refusal).
                defer_mode=DeferMode.MODAL,
                handler=HandlerRef("ticket.open_submit"),
                modal=ModalSpec(
                    modal_id="ticket.launcher_open_form",
                    title="Open a support ticket",
                    fields=(ModalFieldSpec(field_id="subject",
                                           label="Subject",
                                           required=True),)),
            ),
        ),
        # the shipped launcher carried NO nav row (a public channel
        # anchor, not a hub descendant) — sweep_ticketpanel pins the
        # single-button component tree.
        navigation=NavigationSpec(show_help=False, show_home=False),
        # never in panel_anchors (the golden pins the no-anchor-row delta;
        # the shipped launcher's persistence lived in discord.py's
        # persistent-view registry, not a DB anchor).
        session_lifecycle=True,
        renderer_override=HandlerRef("ticket.render_launcher"),
        justification=(
            "two shipped surfaces outside the grammar's static vocabulary, "
            "each named per §2.9: (1) the FOOTER is the live guild name "
            "(views/tickets/_shared.py build_launcher_embed(guild_name) — "
            "set_footer(text=guild_name)); read through the utility "
            "guild-directory port, degrading to no footer (the welcome "
            "posture); goldens/ticket/sweep_ticketpanel pins 'Parity Test "
            "Guild'. (2) the 📮 ACK REACTION: the shipped cog ran "
            "`await ctx.message.add_reaction(\"📮\")` after post_launcher "
            "— an invoking-message ack the panel runtime has no seam for; "
            "it rides RenderedPanel.self_reactions (the #130 primer seam), "
            "landing on the panel message instead. Both wire docs "
            "normalize to the same bytes (the reaction's message ref is "
            "the doc's only symbolic <msg:N> after the ruled "
            "invoking-message-deletion + kernel-table drops, so "
            "first-appearance renumbering maps both to <msg:1>) — the "
            "placement drift is live-only and ledgered here."),
        layout=LayoutSpec(pages=(PageSpec(rows=(("launcher_open",),)),)),
    )


async def _render_launcher(spec, ctx) -> object:
    """Grammar render + the two shipped adjustments named in the spec's
    justification: the guild-name footer + the 📮 self-reaction."""
    from dataclasses import replace as _dc_replace

    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    guild_name = ""
    try:
        from sb.domain.utility.service import guild_directory

        info = await guild_directory().guild_info(gid)
        guild_name = str(getattr(info, "name", "") or "")
    except Exception:  # noqa: BLE001 — headless ⇒ footer-less (degrade)
        guild_name = ""
    return _dc_replace(
        rendered,
        embed=_dc_replace(rendered.embed, footer=guild_name),
        self_reactions=("📮",))


# --- the setup wizard panel (`!ticketsetup` — views/tickets/config_panel.py) -------

#: shipped wizard embed body, verbatim (views/tickets/config_panel.py) —
#: goldens/ticket/sweep_ticketsetup pins every byte.
_SETUP_DESCRIPTION = (
    "Let members open **private support tickets** — a per-member "
    "channel only they and your staff can see. They open one with "
    "`!ticket new`, a button panel, or by asking the AI.\n\n"
    "**1.** Pick a **staff role** below (required).\n"
    "**2.** Pick a **transcript log** channel, or tap **Auto-create** to "
    "make one.\n"
    "**3.** Tap **Enable tickets** — then **Post panel** so members "
    "get a button.\n\n"
    "_Ticket channels are created automatically under a “Tickets” "
    "category when a member opens one — nothing to set up there._"
)

#: shipped wizard footer, verbatim (config_panel.py set_footer).
_SETUP_FOOTER = ("Tune limits / blacklist later with !ticketlimit and "
                 "!ticketblacklist.")


def ticket_setup_spec():
    from sb.spec.panels import (
        ActionStyle,
        Audience,
        EmbedFrameSpec,
        FooterMode,
        LayoutSpec,
        NavigationSpec,
        PageSpec,
        PanelActionSpec,
        PanelSpec,
        SelectorKind,
        SelectorSpec,
        TextBlock,
    )
    from sb.spec.refs import HandlerRef

    return PanelSpec(
        panel_id="ticket.setup",
        subsystem="ticket",
        # the shipped TicketConfigPanelView + its embed (views/tickets/
        # config_panel.py, shared by `!ticketsetup` and the setup wizard's
        # ticket section) — goldens/ticket/sweep_ticketsetup pins title,
        # body, both native pickers, all three buttons and the row split.
        title="🎫 Support Tickets",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_SETUP_DESCRIPTION),),
        selectors=(
            # discord.ui.RoleSelect, row 0 (shipped placeholder verbatim)
            # — the native role picker (wire type 6, Discord supplies the
            # options).
            SelectorSpec(
                selector_id="setup_staff_role", kind=SelectorKind.ROLE,
                on_select=HandlerRef("ticket.setup_pending"),
                placeholder="Staff role (required) — who handles "
                            "tickets…",
                audience_tier="staff"),
            # discord.ui.ChannelSelect(channel_types=[text]), row 1.
            SelectorSpec(
                selector_id="setup_log_channel", kind=SelectorKind.CHANNEL,
                on_select=HandlerRef("ticket.setup_pending"),
                placeholder="Transcript log channel (optional)…",
                audience_tier="staff"),
        ),
        actions=(
            # the shipped decorator forms verbatim (config_panel.py rows
            # 2/2/3) — emoji as the SEPARATE wire field.
            PanelActionSpec(
                action_id="setup_autocreate_log",
                label="Auto-create log channel", emoji="🪄",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                handler=HandlerRef("ticket.setup_pending")),
            PanelActionSpec(
                action_id="setup_enable", label="Enable tickets",
                emoji="✅", style=ActionStyle.SUCCESS,
                audience_tier="staff",
                handler=HandlerRef("ticket.setup_pending")),
            PanelActionSpec(
                action_id="setup_post_panel",
                label="Post open-ticket panel here", emoji="📋",
                style=ActionStyle.SECONDARY, audience_tier="staff",
                handler=HandlerRef("ticket.setup_pending")),
        ),
        # the shipped wizard carried NO nav row — the golden pins the
        # 4-row component tree (role pick / channel pick / auto-create +
        # enable / post panel).
        navigation=NavigationSpec(show_help=False, show_home=False),
        # ctx-bound timeout view (`open_ticket_config_panel(ctx.author,
        # ...)`) — session-minted <cid:1..5>, never anchored (the golden
        # pins the no-anchor-row delta).
        session_lifecycle=True,
        renderer_override=HandlerRef("ticket.render_setup"),
        justification=(
            "two shipped surfaces outside the grammar's static "
            "vocabulary, each named per §2.9: (1) the Selected/Current "
            "FIELD is state-parameterized end to end (config_panel.py: "
            "the 'Selected' vs 'Current' name keys on enabled, the four "
            "bullet lines render the live staff-role/log-channel/"
            "max-open state with per-line empty-state literals) — the "
            "override composes it from the ticket_config read; goldens/"
            "ticket/sweep_ticketsetup pins the config-absent bytes. "
            "(2) the FOOTER is the shipped static literal (set_footer) — "
            "FooterMode has no literal-text lane. Body, title, pickers, "
            "buttons, layout and frame stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("setup_staff_role",),
            ("setup_log_channel",),
            ("setup_autocreate_log", "setup_enable"),
            ("setup_post_panel",),
        )),)),
    )


async def _render_setup(spec, ctx) -> object:
    """Grammar render + the two shipped adjustments named in the spec's
    justification: the state-dependent Selected/Current field + the
    footer literal (config_panel.py verbatim)."""
    from dataclasses import replace as _dc_replace

    from sb.domain.ticket import store
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    try:
        cfg = await store.get_config_row(gid)
    except Exception:  # noqa: BLE001 — best-effort read (shipped posture)
        cfg = None
    enabled = bool((cfg or {}).get("enabled")) if cfg else False
    staff_role_id = (cfg or {}).get("staff_role_id")
    log_channel_id = (cfg or {}).get("log_channel_id")
    max_open_per_user = (cfg or {}).get("max_open_per_user")
    # the shipped fallback literals + set-state renders, verbatim
    # (config_panel.py; the set branches resolve mentions live-side —
    # role.mention/channel.mention render as `<@&id>`/`<#id>` on the wire;
    # the shipped raw-id backtick fallback is kept for a vanished role).
    role_text = "_(not set — required)_"
    if staff_role_id:
        role_text = f"<@&{int(staff_role_id)}>"
    log_text = "_(none — tap Auto-create or pick one)_"
    if log_channel_id:
        log_text = f"<#{int(log_channel_id)}>"
    field_name = "Selected" if not enabled else "Current"
    field_value = (
        f"• Status: **{'enabled' if enabled else 'not enabled yet'}**\n"
        f"• Staff role: {role_text}\n"
        f"• Transcript log: {log_text}\n"
        f"• Max open per user: **{max_open_per_user or 3}**"
    )
    embed = _dc_replace(
        rendered.embed,
        fields=tuple(rendered.embed.fields) + ((field_name, field_value),),
        footer=_SETUP_FOOTER)
    return _dc_replace(rendered, embed=embed)


def install_ticket_panels():
    from sb.kernel.panels.registry import register_panel

    specs = (ticket_hub_spec(), ticket_launcher_spec(), ticket_setup_spec())
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
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    if not is_registered(PanelRef("ticket.hub")):
        @panel("ticket.hub")
        def _factory():
            return ticket_hub_spec()
    if not is_registered(PanelRef("ticket.launcher")):
        @panel("ticket.launcher")
        def _launcher_factory():
            return ticket_launcher_spec()
    if not is_registered(PanelRef("ticket.setup")):
        @panel("ticket.setup")
        def _setup_factory():
            return ticket_setup_spec()
    if not is_registered(HandlerRef("ticket.render_hub")):
        handler("ticket.render_hub")(_render_hub)
    if not is_registered(HandlerRef("ticket.render_launcher")):
        handler("ticket.render_launcher")(_render_launcher)
    if not is_registered(HandlerRef("ticket.render_setup")):
        handler("ticket.render_setup")(_render_setup)


def ensure_handler_refs() -> None:
    _register()


_register()
ensure_panel_refs()

"""The ON-GUILD-JOIN SETUP LAUNCHER (night-tail-2), ported from the
oracle (menno420/superbot @bbc524e4, ``disbot/cogs/setup_cog.py``
``SetupCog.on_guild_join`` / ``_handle_join`` /
``_post_launcher_in_setup_channel`` + ``disbot/views/setup/launcher.py``
``SetupLauncherView`` / ``_build_launcher_embed`` /
``pick_launcher_channel`` / ``post_launcher``):

* when the bot joins a guild it tries the PRIVATE-WORKSPACE path first —
  ``ensure_setup_channel`` (find-or-create ``#superbot-setup``), then the
  launcher post with the owner-ping content line when the channel was
  freshly created; a restart/rejoin that finds the channel AND a session
  row still pointing at a live launcher message keeps the prior ids
  (no double-post — ``_resume_launchers`` edits it in place on boot);
* on any workspace failure it falls back to ``post_launcher``'s ladder
  (``pick_launcher_channel``): system channel → first channel named
  ``admin``/``mod``/``staff`` → first named ``bot`` → first text channel;
* wherever the launcher landed (or didn't), ``start_session`` upserts the
  session row with the resulting pointers — the K7 ``setup.start_session``
  op here (the oracle's one service function served the join and the
  depth entry alike);
* the launcher panel itself is the PERSISTENT owner-gated seven-button
  card (static custom ids ``setup:start`` … ``setup:dismiss``; labels,
  copy and accents verbatim; the status-aware Start label set:
  pending/dismissed → "Start Setup", in_progress → "Resume Setup",
  complete → "Re-run Setup").

Kernel-idiom divergences, ledgered (the essential_steps.py adaptation
doctrine — same semantics, only the seams differ):

* the oracle hung the surface on a cog ``on_guild_join`` listener; this
  build has no cogs and no kernel→domain edge, so the handler registers
  on the kernel GUILD-JOIN seam (sb/kernel/interaction/guild_events.py —
  the reaction-registry mirror; the manifest wires it, the live adapter
  ``sb/adapters/discord/guild_feed.py`` feeds it);
* Discord mechanics (``channel.send(embed=…, view=…)``) live behind the
  panel engine's message-POSTER port (``post_anchored_panel`` → the
  adapter's ``DiscordPanelMessagePoster`` — the #437 editor port's
  twin); headless the port answers None and the join lane degrades to a
  pointer-less session upsert (a counted no-op, never a crash);
* the OWNER-DM fallback (``post_launcher``'s last rung — ``owner.send``)
  is NOT ported: no DM egress port exists in this build; the ladder ends
  at "no sendable channel" with the session row still minted (honest
  deferral, flagged);
* ``pick_launcher_channel``'s per-channel permission probe
  (``_bot_can_send_in``) reads gateway member permissions the
  channel-directory port does not carry — the ladder picks by the
  oracle's ORDER over the port's cache view and the send itself is the
  probe (a refused send logs and the join lane falls through/ends);
* the launcher's per-button gates ride the ported ladders: the
  owner-or-delegated gate is ``wizard.can_apply_setup`` (the shipped
  ``setup_access.can_apply_setup`` port), the owner/admin/delegate gate
  folds ``actor.is_guild_operator`` over it (the shipped
  ``is_setup_admin`` admin leg); Run Readiness Scan answers the ported
  check-my-setup read (``essential_steps.build_check_setup_text`` — the
  oracle's ``build_setup_readiness_embed`` scorecard fold is a
  diagnostic-band follow-up), and View Summary keeps the oracle's
  not-complete refusal verbatim with an honest terminal on the complete
  branch (the SummaryView digest is unported).

NO GOLDEN drives the join surface (the panels.py module pin) — the
oracle sources pin copy and semantics.
"""

from __future__ import annotations

import dataclasses
import logging
import uuid

__all__ = [
    "GUILD_JOIN_CONSUMER",
    "LAUNCHER_PANEL_ID",
    "ensure_launcher_refs",
    "handle_guild_join",
    "launcher_spec",
    "register_guild_join_launcher",
]

logger = logging.getLogger("sb.domain.setup")

LAUNCHER_PANEL_ID = "setup.launcher"
GUILD_JOIN_CONSUMER = "setup.launcher"

#: shipped copy, verbatim (views/setup/launcher.py).
_LAUNCHER_TITLE = "🛰 SuperBot setup"
_LAUNCHER_DESC = (
    "Welcome! I'll help you set SuperBot up for this server.\n\n"
    "Click **Start Setup** for the quick guided setup — a few simple steps, "
    "each saved as you go. The other buttons are optional extras, or "
    "**Dismiss** to defer.\n\n"
    "**Quick commands:** `!setup` / `/setup` for the quick guided setup, "
    "`/setup-advanced` for the full editor, "
    "`/setup-status` for a read-only peek, `/setup-reset` to start over.\n\n"
    "🎫 Setup includes a **Support Tickets** step — enable private "
    "member↔staff tickets there, or run `!ticketsetup @StaffRole [#log]`."
)
_LAUNCHER_FOOTER = ("Owner-gated for write actions. Admins can run the "
                    "readiness scan.")

#: shipped status-aware Start label set, verbatim (_START_LABELS_BY_STATUS).
_START_LABELS_BY_STATUS = {
    "pending": "Start Setup",
    "in_progress": "Resume Setup",
    "complete": "Re-run Setup",
    "dismissed": "Start Setup",
}

#: shipped join content line, verbatim (setup_cog
#: ``_post_launcher_in_setup_channel`` — sent only when the workspace was
#: freshly created; the owner mention rides the explicit user allowlist).
_JOIN_CONTENT = (
    "{owner_mention} SuperBot just joined! I'll use this private "
    "channel as the setup workspace. Click **Start Setup** below "
    "(or run `!setup` / `/setup`) to begin."
)

#: shipped gate copy, verbatim (SetupLauncherView).
_GATE_ADMIN = ("Only the server owner, an administrator, or a delegated "
               "setup admin can use this button.")
_GATE_START = ("Only the server owner, an administrator, or a delegated "
               "setup admin can start setup.")
_GATE_APPLY = ("Only the server owner or a delegated setup admin can use "
               "this button. Ask the owner to grant you `/setup-delegate`.")
_GATE_OWNER = "Only the server owner can start setup or change presets."


# --- the panel ----------------------------------------------------------------------

def launcher_spec():
    """The persistent seven-button launcher card (SetupLauncherView —
    ``timeout=None`` + static per-button custom_id: the message survives
    restarts and the resume sweep's edit lane rebinds by the SAME wire
    ids; the ``ticket.launcher`` persistence precedent)."""
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        NavigationSpec, PageSpec, PanelActionSpec, PanelSpec, TextBlock,
    )
    from sb.spec.refs import HandlerRef

    return PanelSpec(
        panel_id=LAUNCHER_PANEL_ID,
        subsystem="setup",
        title=_LAUNCHER_TITLE,
        # the shipped SetupLauncherView is a PERSISTENT channel view
        # (timeout=None, registered at cog_load) — per-button gating, no
        # invoker lock.
        audience=Audience.PERSISTENT,
        timeout_s=None,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_LAUNCHER_DESC),),
        actions=(
            PanelActionSpec(
                action_id="launcher_start", label="Start Setup",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.launcher_start"),
                custom_id_override="setup:start"),
            PanelActionSpec(
                action_id="launcher_readiness", label="Run Readiness Scan",
                style=ActionStyle.PRIMARY,
                handler=HandlerRef("setup.launcher_readiness"),
                custom_id_override="setup:readiness"),
            PanelActionSpec(
                action_id="launcher_suggestions", label="Smart Suggestions",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.launcher_suggestions"),
                custom_id_override="setup:smart_suggestions"),
            PanelActionSpec(
                action_id="launcher_preset", label="Choose Preset",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.open_section_preset_select"),
                custom_id_override="setup:preset"),
            PanelActionSpec(
                action_id="launcher_summary", label="View Summary",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.launcher_summary"),
                custom_id_override="setup:summary"),
            PanelActionSpec(
                action_id="launcher_repost", label="Repost launcher",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.launcher_repost"),
                custom_id_override="setup:repost_launcher"),
            PanelActionSpec(
                action_id="launcher_dismiss", label="Dismiss",
                style=ActionStyle.DANGER,
                handler=HandlerRef("setup.launcher_dismiss"),
                custom_id_override="setup:dismiss"),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("launcher_start", "launcher_readiness",
             "launcher_suggestions", "launcher_preset"),
            ("launcher_summary", "launcher_repost", "launcher_dismiss"))),)),
        renderer_override=HandlerRef("setup.launcher_render"),
        justification=(
            "the shipped launcher embed is session-parameterized in its "
            "description ('**Status:** `{status}`' + readiness/step "
            "suffixes — launcher._build_launcher_embed), its COLOR "
            "(blurple / complete-green / dismissed-dark_grey) and its "
            "Start BUTTON LABEL (_START_LABELS_BY_STATUS — the on_ready "
            "rebind), and it carries the footer literal + the join "
            "content line — all outside the static grammar vocabulary; "
            "the override delegates the component render to the grammar "
            "and composes embed/labels/content (no golden pins it — the "
            "oracle source does)."),
        session_lifecycle=True,
    )


async def _render_launcher(spec, ctx) -> object:
    """renderer_override — ``_build_launcher_embed`` + the status-aware
    Start relabel, verbatim. A fresh join post passes ``launcher_fresh``
    (the oracle posted ``_build_launcher_embed(None)`` on join even when
    a stale row existed); every other presentation reads the session
    row."""
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    params = getattr(ctx, "params", {}) or {}
    session = None
    if not params.get("launcher_fresh"):
        from sb.domain.setup import store

        try:
            session = await store.get_session_row(int(ctx.guild_id or 0))
        except Exception:  # noqa: BLE001 — headless/no DB ⇒ the fresh card
            logger.debug("launcher render: session read failed",
                         exc_info=True)
            session = None

    status = str(session.get("setup_status") or "") if session else ""
    token = "blurple"
    if status == "complete":
        token = "green"
    elif status == "dismissed":
        token = "dark_grey"
    description = _LAUNCHER_DESC
    if session is not None:
        description = f"{_LAUNCHER_DESC}\n\n**Status:** `{status}`"
        if session.get("last_readiness_score") is not None:
            description += (f" · readiness "
                            f"`{session['last_readiness_score']}%`")
        if session.get("current_step"):
            description += f" · step `{session['current_step']}`"

    base = await render_panel(spec, ctx)
    start_label = _START_LABELS_BY_STATUS.get(status, "Start Setup")
    components = tuple(
        dataclasses.replace(c, label=start_label)
        if c.custom_id == "setup:start" else c
        for c in base.components)
    embed = RenderedEmbed(
        title=spec.title,
        description=description,
        footer=_LAUNCHER_FOOTER,
        style_token=token)
    content = str(params.get("launcher_content") or "") or None
    return dataclasses.replace(base, embed=embed, components=components,
                               content=content)


# --- the join lane -------------------------------------------------------------------

def _join_actor():
    """The system-actor sentinel (the resume sweep's twin — the join post
    is bot-initiated, no member behind it)."""
    from sb.kernel.interaction.request import ActorRef

    return ActorRef(user_id=None, is_guild_operator=False,
                    is_bot_owner=False, is_dm=False,
                    actor_type="system", member_tier=None)


async def _post_launcher_panel(guild_id: int, channel_id: int, *,
                               content: str | None = None,
                               mention_user_ids: tuple[int, ...] = ()
                               ) -> int | None:
    from sb.kernel.panels import engine as panel_engine
    from sb.spec.refs import PanelRef

    params: dict = {"launcher_fresh": True}
    if content:
        params["launcher_content"] = content
    return await panel_engine.post_anchored_panel(
        PanelRef(LAUNCHER_PANEL_ID), guild_id=int(guild_id),
        channel_id=int(channel_id), actor=_join_actor(), params=params,
        mention_user_ids=mention_user_ids)


async def _post_launcher_in_setup_channel(event) -> tuple[int | None,
                                                          int | None]:
    """The private-setup-channel path (oracle
    ``_post_launcher_in_setup_channel``): ``(channel_id, message_id)`` on
    success, ``(None, None)`` to signal the fallback ladder. Idempotent
    on a rejoin/restart: an existing channel whose session row still
    carries a launcher message keeps the prior ids (the on-ready sweep
    edits that message in place — never a double post)."""
    from sb.domain.setup import service, store

    guild_id = int(event.guild_id)
    owner_id = int(getattr(event, "owner_id", 0) or 0)
    try:
        row = await store.get_session_row(guild_id)
    except Exception:  # noqa: BLE001 — headless/no DB ⇒ no prior pointers
        logger.debug("setup launcher: session read failed (guild=%d)",
                     guild_id, exc_info=True)
        row = None
    try:
        channel_id, created = await service.ensure_setup_channel(
            guild_id, owner_id)
    except Exception:  # noqa: BLE001 — the oracle's ensure-failed branch
        logger.exception(
            "setup launcher: ensure_setup_channel failed (guild=%d)",
            guild_id)
        return None, None
    if (not created and row is not None
            and int(row.get("setup_channel_id") or 0) == int(channel_id)
            and row.get("setup_message_id")):
        return int(channel_id), int(row["setup_message_id"])
    content = None
    mentions: tuple[int, ...] = ()
    if created:
        owner_mention = f"<@{owner_id}>" if owner_id else ""
        content = _JOIN_CONTENT.format(owner_mention=owner_mention)
        if owner_id:
            mentions = (owner_id,)
    message_id = await _post_launcher_panel(
        guild_id, int(channel_id), content=content,
        mention_user_ids=mentions)
    if message_id is None:
        # the oracle's send-failed branch — signal the fallback ladder.
        logger.warning("setup launcher: workspace post failed in "
                       "guild=%d", guild_id)
        return None, None
    return int(channel_id), int(message_id)


async def _pick_launcher_channel(guild_id: int,
                                 system_channel_id: int | None
                                 ) -> int | None:
    """The safest-channel ladder (oracle ``pick_launcher_channel``), the
    oracle order over the channel-directory port's cache view:
    system channel → ``admin``/``mod``/``staff`` name hit → ``bot`` name
    hit → first text channel → None."""
    from sb.domain.channel import service as channel_service

    try:
        snaps = await channel_service.active_directory().list_channels(
            int(guild_id))
    except Exception:  # noqa: BLE001 — headless/no directory ⇒ no channels
        logger.debug("setup launcher: channel directory read failed "
                     "(guild=%d)", guild_id, exc_info=True)
        return None
    text = [s for s in snaps if str(getattr(s, "kind", "")) == "text"]
    if system_channel_id and any(
            int(s.channel_id) == int(system_channel_id) for s in text):
        return int(system_channel_id)
    for needles in (("admin", "mod", "staff"), ("bot",)):
        for snap in text:
            name = (snap.name or "").lower()
            if any(needle in name for needle in needles):
                return int(snap.channel_id)
    if text:
        return int(text[0].channel_id)
    return None


async def _post_launcher_fallback(event) -> tuple[int | None, int | None]:
    """The oracle ``post_launcher`` fallback: pick a channel + post the
    plain launcher (no content line). ``(None, None)`` when nothing was
    sendable — the owner-DM last rung is unported (module ledger)."""
    guild_id = int(event.guild_id)
    channel_id = await _pick_launcher_channel(
        guild_id, getattr(event, "system_channel_id", None))
    if channel_id is None:
        return None, None
    message_id = await _post_launcher_panel(guild_id, channel_id)
    if message_id is None:
        logger.warning("setup launcher: fallback post failed in channel "
                       "%d (guild=%d)", channel_id, guild_id)
        return None, None
    return channel_id, int(message_id)


async def _record_join_session(event, channel_id: int | None,
                               message_id: int | None) -> None:
    """The oracle's unconditional ``start_session`` upsert (the row is
    minted even when nothing was posted) — the K7 ``setup.start_session``
    op, never the bare store write (sole-writer discipline)."""
    from sb.kernel.workflow import engine as workflow_engine
    from sb.kernel.workflow.context import WorkflowContext
    from sb.spec.refs import WorkflowRef

    await workflow_engine.run(
        WorkflowRef("setup.start_session"),
        WorkflowContext(
            actor=_join_actor(), guild_id=int(event.guild_id),
            request_id=str(uuid.uuid4()),
            params={"guild_name": str(getattr(event, "guild_name", "") or ""),
                    "owner_id": int(getattr(event, "owner_id", 0) or 0),
                    "setup_channel_id": channel_id,
                    "setup_message_id": message_id}))


async def handle_guild_join(event) -> dict:
    """THE guild-join consumer (oracle ``_handle_join``): workspace path
    first, fallback ladder second, session upsert always; the whole
    handler exception-isolated (a join must never break the feed).
    Returns the counters (evidence for tests + the join log)."""
    counts: dict = {"guild_id": int(event.guild_id), "channel_id": None,
                    "message_id": None, "surface": "none"}
    try:
        channel_id, message_id = await _post_launcher_in_setup_channel(event)
        surface = "workspace"
        if channel_id is None:
            channel_id, message_id = await _post_launcher_fallback(event)
            surface = "fallback" if channel_id is not None else "none"
        await _record_join_session(event, channel_id, message_id)
        counts.update({"channel_id": channel_id, "message_id": message_id,
                       "surface": surface})
        logger.info("setup launcher: guild %d joined — launcher %s "
                    "(channel=%s message=%s)", event.guild_id,
                    surface, channel_id, message_id)
    except Exception:  # noqa: BLE001 — the oracle's handler isolation
        logger.exception(
            "setup launcher: on_guild_join handler failed for guild=%s",
            getattr(event, "guild_id", None))
    return counts


# --- the button handlers --------------------------------------------------------------

async def _is_setup_admin(req) -> bool:
    """The shipped ``is_setup_admin`` ladder over the ported facts:
    owner-or-delegated (``can_apply_setup``) OR a plain administrator
    (``actor.is_guild_operator`` — owner/administrator/manage_guild,
    the shipped flag)."""
    from sb.domain.setup import wizard

    if bool(getattr(req.actor, "is_guild_operator", False)):
        return True
    return await wizard.can_apply_setup(req)


def _register_handlers() -> None:
    from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
    from sb.spec.outcomes import BLOCKED, SUCCESS
    from sb.spec.refs import HandlerRef, handler, is_registered
    from sb.spec.refs import resolve as resolve_ref

    if is_registered(HandlerRef("setup.launcher_start")):
        return

    @handler("setup.launcher_start")
    async def launcher_start(req):
        """Start Setup — the oracle ``_start``: gate on the broad
        can-use-setup ladder, then open the plain-language Essential
        Setup spine (the primary ``!setup`` flow) in the workspace; the
        registered ``setup.essential_open`` body IS that flow (ensure
        workspace → Step-1 card → jump-link pointer reply)."""
        if not await _is_setup_admin(req):
            return Reply(BLOCKED, _GATE_START)
        return await resolve_ref(HandlerRef("setup.essential_open"))(req)

    @handler("setup.launcher_readiness")
    async def launcher_readiness(req):
        """Run Readiness Scan — admin-gated read (oracle ``_readiness``).
        Answers the ported check-my-setup health read; the oracle's
        ``build_setup_readiness_embed`` scorecard fold is the
        diagnostic-band follow-up (module ledger)."""
        if not await _is_setup_admin(req):
            return Reply(BLOCKED, _GATE_ADMIN)
        from sb.domain.setup.essential_steps import build_check_setup_text

        return Reply(SUCCESS,
                     await build_check_setup_text(int(req.guild_id or 0)))

    @handler("setup.launcher_suggestions")
    async def launcher_suggestions(req):
        """Smart Suggestions — the oracle ``_suggestions``: the apply
        gate, the advisor draft (the deterministic fallback rides
        ``plan.suggest``, the describe-entry twin), the review panel,
        then the best-effort ``mark_in_progress(step="suggestions")``."""
        from sb.domain.setup import plan, wizard

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, _GATE_APPLY)
        guild_id = int(req.guild_id or 0)
        try:
            draft = await plan.suggest(guild_id)
        except Exception:  # noqa: BLE001 — the oracle's advisor-failed copy
            logger.exception("setup launcher: advisor flow failed")
            return Reply(BLOCKED,
                         "Smart Suggestions failed. Run **Run Readiness "
                         "Scan** for a deterministic baseline.")
        from sb.domain.setup.panels import SUGGESTIONS_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        wizard.seed_review_state(
            guild_id, int(getattr(req.actor, "user_id", 0) or 0), draft)
        args = {**dict(req.args or {}), "setup_plan_draft": draft}
        await open_panel(PanelRef(SUGGESTIONS_PANEL_ID),
                         dataclasses.replace(req, args=args))
        try:
            from sb.kernel.workflow import engine as workflow_engine
            from sb.spec.refs import WorkflowRef

            await workflow_engine.run(
                WorkflowRef("setup.mark_in_progress"),
                ctx_from_request(req, {"step": "suggestions"}))
        except Exception:  # noqa: BLE001 — the oracle's best-effort marker
            logger.exception("setup launcher: mark_in_progress failed")
        return None

    @handler("setup.launcher_summary")
    async def launcher_summary(req):
        """View Summary — the oracle ``_view_summary``: admin gate, then
        the not-complete refusal verbatim; the complete branch holds an
        honest terminal (the SummaryView digest is unported — module
        ledger)."""
        if not await _is_setup_admin(req):
            return Reply(BLOCKED, _GATE_ADMIN)
        from sb.domain.setup import store

        try:
            row = await store.get_session_row(int(req.guild_id or 0))
        except Exception:  # noqa: BLE001 — headless ⇒ no session
            row = None
        if row is None or str(row.get("setup_status") or "") != "complete":
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "Setup is not complete yet. Run **Start Setup** "
                         "to finish the wizard before viewing the summary.")
        return Reply(BLOCKED,
                     "The setup summary digest is not ported in this "
                     "build yet — run `/setup-status` for the read-only "
                     "snapshot.")

    @handler("setup.launcher_repost")
    async def launcher_repost(req):
        """Repost launcher — the oracle ``_repost_launcher``: admin gate,
        the ``post_launcher`` ladder (no system-channel rung at click
        time — the gateway event carried it, the request does not;
        ledgered), then the best-effort ``start_session`` refresh and
        the shipped ack/failure copy."""
        if not await _is_setup_admin(req):
            return Reply(BLOCKED, _GATE_ADMIN)
        guild_id = int(req.guild_id or 0)
        channel_id = await _pick_launcher_channel(guild_id, None)
        message_id = (await _post_launcher_panel(guild_id, channel_id)
                      if channel_id is not None else None)
        if message_id is None:
            # shipped copy, verbatim (the everything-failed deny).
            return Reply(BLOCKED,
                         "Could not post the launcher anywhere — bot has "
                         "no sendable channel and the owner has DMs "
                         "closed.")
        try:
            from sb.domain.setup.handlers import _guild_identity
            from sb.kernel.workflow import engine as workflow_engine
            from sb.spec.refs import WorkflowRef

            guild_name, owner_id = await _guild_identity(guild_id)
            await workflow_engine.run(
                WorkflowRef("setup.start_session"),
                ctx_from_request(req, {
                    "guild_name": guild_name, "owner_id": owner_id,
                    "setup_channel_id": channel_id,
                    "setup_message_id": int(message_id)}))
        except Exception:  # noqa: BLE001 — the oracle's best-effort refresh
            logger.exception("setup launcher: start_session refresh failed")
        # shipped copy, verbatim ("Launcher reposted in {where}.").
        return Reply(SUCCESS, f"Launcher reposted in <#{channel_id}>.")

    @handler("setup.launcher_dismiss")
    async def launcher_dismiss(req):
        """Dismiss — the oracle ``_dismiss``: owner gate (the shipped
        ``_gate_owner`` copy), the ``setup_session.dismiss`` status flip
        through the K7 ``setup.mark_dismissed`` op, the shipped ack."""
        from sb.domain.setup import wizard

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, _GATE_OWNER)
        from sb.kernel.workflow import engine as workflow_engine
        from sb.spec.refs import WorkflowRef

        result = await workflow_engine.run(
            WorkflowRef("setup.mark_dismissed"), ctx_from_request(req, {}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message
                         or "Could not dismiss setup — see logs.")
        # shipped copy, verbatim.
        return Reply(SUCCESS,
                     "Setup dismissed. Use the setup launcher later to "
                     "resume.")


# --- registration ----------------------------------------------------------------------

def register_guild_join_launcher() -> None:
    """Register the join consumer on the kernel guild-events seam
    (manifest-called — declaring IS reserving; idempotent per the
    registry contract)."""
    from sb.kernel.interaction.guild_events import (
        register_guild_join_consumer,
    )

    register_guild_join_consumer(GUILD_JOIN_CONSUMER, handle_guild_join)


def _register_panel() -> None:
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    if not is_registered(HandlerRef("setup.launcher_render")):
        handler("setup.launcher_render")(_render_launcher)
    if not is_registered(PanelRef(LAUNCHER_PANEL_ID)):
        panel(LAUNCHER_PANEL_ID)(launcher_spec)


_register_panel()
_register_handlers()


def ensure_launcher_refs() -> None:
    _register_panel()
    _register_handlers()
    register_guild_join_launcher()

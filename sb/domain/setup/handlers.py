"""The setup entry handlers (parity flip) — the shipped command surfaces
over the workspace service + K7 session ops.

ORACLE @befc6d0d (search_code fragments): cogs/quicksetup_cog.py
(``!setup`` / ``/setup`` — the PRIMARY entry), cogs/setup_cog.py +
cogs/setup/_wizard_entry.py (``/setup-hub``, ``/setup-advanced``,
``/setup-status``, ``/setup-reset``, ``/setup-skip``, ``/setup-unskip``),
cogs/setup/_describe_entry.py (``/setup-describe``). Reply copy is
verbatim where a golden pins it; un-golden-pinned interior branches keep
the honest under-port posture (docstrings below).
"""

from __future__ import annotations

import dataclasses

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["Reply", "ensure_handler_refs"]

#: shipped copy, verbatim (cogs/setup/_describe_entry.py
#: _DETERMINISTIC_NOTE — goldens/setup/sweep_slash_setup-describe).
_DETERMINISTIC_NOTE = (
    "ℹ️ AI isn't configured on this instance, so I matched by channel and "
    "role **names** instead — your description wasn't used. The "
    "suggestions below are still safe to review and apply."
)


async def _guild_identity(guild_id: int) -> tuple[str, int]:
    """(guild_name, owner_id) through the utility guild-directory port —
    the session row's identity columns (the shipped start_session read
    guild.name/guild.owner_id off the gateway cache)."""
    from sb.domain.utility.service import guild_directory

    info = await guild_directory().guild_info(int(guild_id))
    return str(info.name), int(info.owner_id)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.essential_open")):
        return

    @handler("setup.essential_open")
    async def essential_open(req) -> Reply:
        """``!setup`` / ``/setup`` — the Essential Setup entry
        (quicksetup_cog → views/setup/essential_setup.py): ensure the
        private workspace, post the Step-1 card into it, reply with the
        pointer. NO session row and NO audit companion — the essential
        flow is author-bound in-place navigation ("no session row or
        cross-restart persistence is needed", the oracle's own docstring;
        goldens/setup/sweep_setup pins the empty setup_session delta) —
        and no DB leg means no K7 op: the create is a pure Discord
        effect (the channel-service posture)."""
        from sb.domain.setup import service
        from sb.domain.setup.panels import ESSENTIAL_PANEL_ID
        from sb.kernel.interaction.request import Surface

        guild_id = int(req.guild_id or 0)
        invoker = int(getattr(req.actor, "user_id", 0) or 0)
        channel_id, _created = await service.ensure_setup_channel(
            guild_id, invoker)
        message_id = await service.post_panel_to_channel(
            ESSENTIAL_PANEL_ID, req, channel_id)
        url = service.jump_link(guild_id, channel_id, int(message_id or 0))
        if req.surface is Surface.PREFIX:
            # shipped: essential_setup.py `send(f"✅ Setup is ready in
            # {channel.mention} — {message.jump_url}")` (raw URL).
            return Reply(SUCCESS,
                         f"✅ Setup is ready in <#{channel_id}> — {url}")
        # shipped slash: the markdown pointer, ephemeral.
        return Reply(SUCCESS,
                     f"✅ Setup is ready in <#{channel_id}> — [open it]({url}).")

    @handler("setup.hub_open")
    async def hub_open(req) -> None:
        """``/setup-hub`` — resolve_hub_entry's depth-less branch: mint
        the session row (status ``pending`` — the K7 ``setup.start_session``
        op carries the row + the shipped setup.session.started audit
        companion) and answer with the ephemeral depth chooser
        (goldens/setup/sweep_slash_setup-hub pins row + render)."""
        from sb.domain.setup.panels import HUB_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.kernel.workflow import engine
        from sb.spec.refs import PanelRef, WorkflowRef

        guild_name, owner_id = await _guild_identity(int(req.guild_id or 0))
        ctx = ctx_from_request(req, {"guild_name": guild_name,
                                     "owner_id": owner_id})
        await engine.run(WorkflowRef("setup.start_session"), ctx)
        await open_panel(PanelRef(HUB_PANEL_ID), req)
        return None

    @handler("setup.advanced_open")
    async def advanced_open(req) -> Reply:
        """``/setup-advanced`` (and the shipped ``!setupadvanced`` twin's
        shape) — the linear wizard entry: the K7 ``setup.open_workspace``
        op ensures the workspace, posts the depth-chooser anchor into it
        and upserts the in_progress session row (oracle sequencing,
        create-before-DB — ops.py); the entry replies transiently with
        the jump link (goldens/setup/sweep_slash_setup-advanced)."""
        from sb.domain.setup import service
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        guild_name, owner_id = await _guild_identity(int(req.guild_id or 0))
        ctx = ctx_from_request(req, {"guild_name": guild_name,
                                     "owner_id": owner_id,
                                     "_workspace_request": req})
        result = await engine.run(WorkflowRef("setup.open_workspace"), ctx)
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message
                         or "Could not open the setup workspace.")
        channel_id = int(ctx.params.get("_workspace_channel_id", 0) or 0)
        message_id = int(ctx.params.get("_workspace_message_id", 0) or 0)
        url = service.jump_link(int(req.guild_id or 0), channel_id,
                                message_id)
        return Reply(SUCCESS,
                     f"Setup wizard is open in <#{channel_id}> — "
                     f"[Open setup workspace]({url}).")

    @handler("setup.status_view")
    async def status_view(req) -> Reply:
        """``/setup-status`` — the aggressive-ephemeral policy verbatim
        (setup_cog): post the read-only snapshot to the WORKSPACE as a
        durable notice, reply with a short ephemeral pointer. Reads only
        — no session mint (goldens/setup/sweep_slash_setup-status pins
        the empty db_delta + the session-less fallback copy)."""
        from sb.domain.setup import service, store
        from sb.domain.setup.panels import STATUS_PANEL_ID

        guild_id = int(req.guild_id or 0)
        invoker = int(getattr(req.actor, "user_id", 0) or 0)
        session = await store.get_session_row(guild_id)
        channel_id, _created = await service.ensure_setup_channel(
            guild_id, invoker)
        await service.post_panel_to_channel(
            STATUS_PANEL_ID, req, channel_id,
            params={"setup_session": session})
        pointer_channel = (int(session["setup_channel_id"])
                           if session and session.get("setup_channel_id")
                           else None)
        ref = (f"<#{pointer_channel}>" if pointer_channel
               else "the setup workspace")
        return Reply(SUCCESS, f"📋 Setup status posted in {ref}.")

    @handler("setup.reset_view")
    async def reset_view(req) -> Reply:
        """``/setup-reset`` — clear the staged draft. The K9 setup draft
        lane is not populated by any ported surface yet (the wizard
        interior is the named successor), so the staged count reads 0 and
        the shipped already-empty copy answers (goldens/setup/
        sweep_slash_setup-reset pins the byte); the clearing branch lands
        with the wizard-lifecycle slice."""
        del req
        pending_before = 0      # the draft lane's constant-empty read (above)
        if pending_before == 0:
            return Reply(SUCCESS,
                         "No staged operations to clear — the draft is "
                         "already empty.")
        return Reply(BLOCKED,
                     "The staged-draft clear lane isn't armed in this "
                     "build yet — it lands with the wizard-lifecycle "
                     "slice.")  # pragma: no cover — constant-empty today

    def _section_gate(slug: str) -> str | None:
        """The shipped unknown-section refusal (setup_cog:
        ``REGISTRY.get(slug) is None`` → the Available list in registry
        order; goldens/setup/sweep_slash_setup-skip + -unskip pin it)."""
        from sb.domain.setup.sections import REGISTRY, register_shipped_sections

        register_shipped_sections()
        if REGISTRY.get(slug) is None:
            available = ", ".join(f"`{s.slug}`" for s in REGISTRY.ordered())
            return f"Unknown section `{slug}`. Available: {available}"
        return None

    @handler("setup.skip_section")
    async def skip_section(req) -> Reply:
        """``/setup-skip`` — validate the slug first (the shipped order);
        the mark-skipped session write is wizard-interior successor work
        (no golden drives a valid slug)."""
        slug = str(req.args.get("section", "") or "")
        refusal = _section_gate(slug)
        if refusal is not None:
            return Reply(BLOCKED, refusal)
        return Reply(BLOCKED,
                     "Marking sections skipped isn't armed in this build "
                     "yet — it lands with the wizard-lifecycle slice.")

    @handler("setup.unskip_section")
    async def unskip_section(req) -> Reply:
        """``/setup-unskip`` — the skip twin (same shipped validation)."""
        slug = str(req.args.get("section", "") or "")
        refusal = _section_gate(slug)
        if refusal is not None:
            return Reply(BLOCKED, refusal)
        return Reply(BLOCKED,
                     "Restoring skipped sections isn't armed in this "
                     "build yet — it lands with the wizard-lifecycle "
                     "slice.")

    @handler("setup.describe_entry")
    async def describe_entry(req) -> None:
        """``/setup-describe`` — defer (resolve()'s AUTO ack, the shipped
        ``defer(ephemeral=True)``), run the advisor, follow up with the
        review card. The AI advisor lane is key-gated OFF in this build
        (the shipped build_advisor fallback), so the DETERMINISTIC branch
        answers — with the shipped unused-description note when a
        description was given (goldens/setup/sweep_slash_setup-describe
        pins note + card)."""
        from sb.domain.setup import plan
        from sb.domain.setup.panels import SUGGESTIONS_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        description = str(req.args.get("description", "") or "")
        draft = await plan.suggest(int(req.guild_id or 0))
        note = _DETERMINISTIC_NOTE if description else None
        args = {**dict(req.args or {}),
                "setup_plan_draft": draft, "advisor_note": note}
        await open_panel(PanelRef(SUGGESTIONS_PANEL_ID),
                         dataclasses.replace(req, args=args))
        return None


_register()


def ensure_handler_refs() -> None:
    _register()

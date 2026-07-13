"""The setup ON-READY RESUME SWEEP (ORDER 019 item 5a), ported from the
oracle (menno420/superbot @bbc524e4, ``disbot/cogs/setup_cog.py``
``SetupCog.on_ready``):

* leg 1 — ``_resume_launchers``: refresh every guild's persisted
  workspace-anchor message IN PLACE with a fresh state-correct render
  (the oracle edited the launcher embed + status-aware
  ``SetupLauncherView`` label rebind; failures isolated per guild, a
  gone message logs and SKIPS — the launcher leg never clears the
  session pointers);
* leg 2 — ``revive_essential_flows`` (views/setup/essential_setup.py):
  edit every interrupted Essential Setup flow message to the persistent
  ⏸️ **Setup paused** / ▶ Resume bridge (the ``essential_setup:resume``
  compat-pinned button the essential-steps slice armed) so the operator
  picks up at the saved ``essential_step`` after a restart (migration
  099); a VANISHED message clears the anchor so the sweep stops
  retrying it (the oracle ``discord.NotFound`` →
  ``clear_essential_anchor`` branch — here the audited K7
  ``setup.clear_essential_anchor`` op).

Kernel-idiom divergences, ledgered (the essential_steps.py adaptation
doctrine — same semantics, only the seams differ):

* the oracle hung the sweep on a cog ``on_ready`` listener; this build
  has no cogs and no kernel→domain edge, so the sweep registers on the
  kernel BOOT-HOOK seam (sb/kernel/lifecycle/boot_hooks.py — the
  manifest wires it, the composition root fires it once RUNNING);
* the oracle walked ``bot.guilds`` and read each row; the durable
  ``setup_session`` rows already know which guilds carry pointers, so
  ONE roster read (``store.list_resumable_sessions``) replaces the
  guild walk — same per-guild isolation, same skip semantics;
* the oracle's launcher leg rebuilt ``SetupLauncherView(status=...)`` +
  ``_build_launcher_embed(session)``; the on-join launcher surface is
  NOT ported in this build (no ``on_guild_join`` feed is armed), so the
  target's ``setup_message_id`` points at the WORKSPACE ANCHOR the
  advanced entry posts (``setup.hub``, the depth chooser —
  ops.record_workspace_open) and the refresh re-renders THAT panel
  fresh; its buttons rebind by static ``custom_id_override`` exactly
  like the oracle's persistent view (labels are state-independent on
  this card — the launcher panel's status-aware label set follows the
  launcher port itself, the flagged follow-up);
* Discord mechanics (``fetch_message`` → ``edit``) live behind the
  kernel panel engine's message-editor port
  (``edit_anchored_panel`` → the adapter's
  ``DiscordPanelMessageEditor``); headless the port answers
  ``unavailable`` and the sweep degrades to a counted no-op.

NO GOLDEN drives the sweep (the panels.py module pin) — the oracle
sources pin the semantics.
"""

from __future__ import annotations

import logging
import uuid

__all__ = [
    "BOOT_HOOK_NAME",
    "register_setup_boot_hook",
    "run_resume_sweep",
]

logger = logging.getLogger("sb.domain.setup")

BOOT_HOOK_NAME = "setup.resume_sweep"


def _sweep_actor():
    """The system-actor sentinel (the K6 scripted-bypass class — the
    sweep is bot-initiated recovery, no member behind it)."""
    from sb.kernel.interaction.request import ActorRef

    return ActorRef(user_id=None, is_guild_operator=False,
                    is_bot_owner=False, is_dm=False,
                    actor_type="system", member_tier=None)


async def _resume_one_launcher(row: dict) -> bool:
    """Refresh one guild's workspace-anchor message (the oracle
    ``_resume_one_launcher``). True when the message was edited; False
    when the row carries no anchor pair, the message is gone, or the
    edit could not be applied — a gone message only LOGS (the oracle's
    launcher leg never cleared the session pointers)."""
    from sb.domain.setup.panels import HUB_PANEL_ID
    from sb.kernel.panels import engine as panel_engine
    from sb.spec.refs import PanelRef

    guild_id = int(row.get("guild_id") or 0)
    channel_id = row.get("setup_channel_id")
    message_id = row.get("setup_message_id")
    if not channel_id or not message_id:
        return False
    outcome = await panel_engine.edit_anchored_panel(
        PanelRef(HUB_PANEL_ID), guild_id=guild_id,
        channel_id=int(channel_id), message_id=int(message_id),
        actor=_sweep_actor())
    if outcome == panel_engine.EDIT_EDITED:
        return True
    if outcome == panel_engine.EDIT_MISSING:
        logger.info("setup resume: launcher message %s in guild %d is gone.",
                    message_id, guild_id)
    return False


async def _revive_one_essential(row: dict) -> bool:
    """Edit one guild's interrupted Essential Setup message to the Resume
    bridge (the oracle ``revive_one_essential_flow``). True when revived;
    False when there is no in-flight flow, the ids are missing, or the
    message can't be edited. A VANISHED message clears the anchor through
    the audited K7 op so the sweep stops retrying it."""
    from sb.domain.setup.essential_steps import RESUME_PANEL_ID
    from sb.kernel.panels import engine as panel_engine
    from sb.spec.refs import PanelRef

    guild_id = int(row.get("guild_id") or 0)
    channel_id = row.get("setup_channel_id")
    message_id = row.get("essential_message_id")
    if not channel_id or not message_id:
        return False
    outcome = await panel_engine.edit_anchored_panel(
        PanelRef(RESUME_PANEL_ID), guild_id=guild_id,
        channel_id=int(channel_id), message_id=int(message_id),
        actor=_sweep_actor())
    if outcome == panel_engine.EDIT_EDITED:
        return True
    if outcome == panel_engine.EDIT_MISSING:
        logger.info("setup revive: message %s in guild %d is gone; "
                    "clearing.", message_id, guild_id)
        await _clear_essential_anchor(guild_id)
    return False


async def _clear_essential_anchor(guild_id: int) -> None:
    """The oracle's NotFound branch write — the K7
    ``setup.clear_essential_anchor`` op (never the bare store write:
    sole-writer discipline). Best-effort like every sweep leg."""
    from sb.kernel.workflow import engine as workflow_engine
    from sb.kernel.workflow.context import WorkflowContext
    from sb.spec.refs import WorkflowRef

    try:
        await workflow_engine.run(
            WorkflowRef("setup.clear_essential_anchor"),
            WorkflowContext(actor=_sweep_actor(), guild_id=int(guild_id),
                            request_id=str(uuid.uuid4()), params={}))
    except Exception:  # noqa: BLE001 — the oracle's own isolation posture
        logger.exception("setup revive: clear_essential_anchor failed "
                         "(guild=%d)", guild_id)


async def run_resume_sweep() -> dict:
    """THE boot hook: both oracle sweeps in the oracle order (launchers
    first, then the essential revive), per-guild failures isolated.
    Returns the counters (evidence for the boot log + tests)."""
    from sb.domain.setup import store

    rows = await store.list_resumable_sessions()
    counts = {"rows": len(rows), "launchers_resumed": 0,
              "essential_revived": 0, "errors": 0}
    for row in rows:
        try:
            if await _resume_one_launcher(row):
                counts["launchers_resumed"] += 1
        except Exception:  # noqa: BLE001 — per-guild isolation (the oracle)
            counts["errors"] += 1
            logger.exception("setup resume: launcher resume failed for "
                             "guild=%s", row.get("guild_id"))
    for row in rows:
        try:
            if await _revive_one_essential(row):
                counts["essential_revived"] += 1
        except Exception:  # noqa: BLE001 — per-guild isolation (the oracle)
            counts["errors"] += 1
            logger.exception("setup revive: revive failed for guild=%s",
                             row.get("guild_id"))
    if counts["rows"]:
        logger.info("setup resume sweep: %(rows)d row(s) — "
                    "%(launchers_resumed)d launcher(s) refreshed, "
                    "%(essential_revived)d essential flow(s) revived, "
                    "%(errors)d error(s)", counts)
    return counts


def register_setup_boot_hook() -> None:
    """Register the sweep on the app-boot seam (manifest-called —
    declaring IS reserving; idempotent per the registry contract)."""
    from sb.kernel.lifecycle import boot_hooks

    boot_hooks.register_boot_hook(BOOT_HOOK_NAME, run_resume_sweep)

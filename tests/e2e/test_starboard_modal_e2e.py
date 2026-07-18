"""D5.1 modal-submit exemplar — a `starboard.threshold_form` MODAL driven
end-to-end through the REAL discord adapter.

The tier's other exemplars drive prefix / slash / component-click / write; this
one closes the last untested adapter interaction type: a **modal submit**. It
grounds the flow in the real corpus:

  `!starboard panel` (staff) opens the real `starboard.config` panel → the
  panel's `✏️ Threshold` action declares `THRESHOLD_MODAL`, materialized by the
  REAL `sb/adapters/discord/modal_view.build_modal` into a real
  `discord.ui.Modal` (the real modal-open the golden-parity fake transport can
  never render — D5 doc P1) → a real channel-pick component click configures the
  hall-of-fame channel (default threshold 3) → `Harness.modal_submit` re-enters
  through the frozen modal adapter (`dispatch_modal`) → the real
  `starboard.panel_threshold` handler runs the audited `starboard.configure` K7
  write (real Postgres) → `_reopen` re-renders `starboard.config` through the
  real `build_embed`.

Starboard is a stable, unclaimed, settings-adjacent domain — outside the claimed
test-depth scopes (fishing / role / casino / blackjack / rps / server_management
/ xp) and off the btd6 test-depth-adjacent modal.
"""

from __future__ import annotations

import asyncio

from tests.e2e.conftest import boot_e2e_harness


def _threshold_action():
    """The real `✏️ Threshold` PanelActionSpec off the live starboard.config
    panel definition — so the modal we materialize is the one the command's
    panel actually declares, not an invented spec."""
    from sb.domain.starboard.panels import config_panel_spec

    spec = config_panel_spec()
    action = next(a for a in spec.actions
                  if a.action_id == "starboard_threshold")
    assert action.modal is not None            # the panel declares the form
    return action


def test_starboard_threshold_modal_submits_through_real_adapter() -> None:
    async def _body() -> None:
        harness, recorder = await boot_e2e_harness()
        try:
            import discord

            from sb.adapters.discord import modal_view
            from sb.domain.starboard import service

            guild_id = harness.world.guild_id
            channel_id = harness.world.channels["general"]

            # 1) the command opens the real starboard.config panel — captured
            #    through the REAL panel_view (real discord.Embed + real View).
            await harness.send_command("!starboard panel", persona="admin")
            cap = recorder.panel("starboard.config")
            assert isinstance(cap.embed, discord.Embed)
            assert cap.embed.title == "⭐ Starboard config"
            assert type(cap.view).__name__ == "PanelRuntimeView"

            # 2) the panel's ✏️ Threshold action declares the real
            #    THRESHOLD_MODAL — materialize it through the REAL adapter
            #    (modal_view.build_modal): a real discord.ui.Modal carrying the
            #    `threshold` TextInput. This is the "real modal open" P1's fake
            #    transport can never exercise.
            modal_spec = _threshold_action().modal
            modal = modal_view.build_modal(modal_spec)
            assert isinstance(modal, discord.ui.Modal)
            assert type(modal).__module__ == "sb.adapters.discord.modal_view"
            assert modal.custom_id == "starboard.threshold_form"
            assert modal.title == "Starboard threshold"
            assert len(modal.children) == 1
            field = modal.children[0]
            assert isinstance(field, discord.ui.TextInput)
            assert field.custom_id == "threshold"
            assert modal_spec.fields[0].field_id == "threshold"

            # 3) a real channel-pick component click configures the
            #    hall-of-fame channel (the submit's PRE-modal guard needs it):
            #    default threshold 3.
            await harness.click(
                message_id=910,
                custom_id="starboard.config.starboard_pick_channel",
                component_type=8, values=[str(channel_id)], persona="admin")
            configured = await service.get_settings(guild_id)
            assert configured is not None
            assert configured["channel_id"] == channel_id
            assert configured["threshold"] == 3

            # 4) the MODAL SUBMIT — wire-type-5 re-entry through the frozen
            #    modal adapter → the real starboard.panel_threshold handler →
            #    the audited starboard.configure K7 write.
            await harness.modal_submit(
                message_id=910, custom_id="starboard.threshold_form",
                fields={"threshold": "7"}, persona="admin")

            # 5a) the real persisted write: the K7 op moved the threshold.
            persisted = await service.get_settings(guild_id)
            assert persisted is not None
            assert persisted["threshold"] == 7
            assert persisted["channel_id"] == channel_id

            # 5b) the real egress: the submit's `_reopen` re-rendered
            #     starboard.config through the REAL build_embed, and the new
            #     threshold shows in the configured-state description.
            reopened = [c for c in recorder.panels
                        if c.panel_id == "starboard.config"][-1]
            assert isinstance(reopened.embed, discord.Embed)
            assert "≥ **7**" in (reopened.embed.description or "")
            assert f"<#{channel_id}>" in (reopened.embed.description or "")
        finally:
            await harness.close()

    asyncio.run(_body())

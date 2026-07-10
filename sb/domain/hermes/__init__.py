"""HERMES subsystem — the Discord→Claude-Code dispatch bridge surface.

Shipped home: disbot/cogs/hermes_cog.py (`/bugreport` + `/dispatch`, both
admin-gated slash commands that POST a work order to the Claude Code
Routine ``/fire`` endpoint). The parity corpus pins the unconfigured-bridge
reply (parity/goldens/hermes/) — deferred ephemeral ack + the red
"Hermes bridge not configured" embed followup.
"""

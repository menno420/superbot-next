"""Hermes dispatch-bridge service — config presence + the shipped
missing-config help copy (disbot/cogs/hermes_cog.py, verbatim).

The shipped `_fire_work_order` gate was `if not fire_url or not token:
raise RuntimeError("missing_config")`; this module ports that presence
check as a boot-installed seam (the ``install_owner_config`` module-state
pattern). UNINSTALLED fails closed — ``bridge_configured() == False`` —
which is also the parity harness's posture (the goldens pin the
unconfigured reply).

The configured path's outbound POST (the Claude Code Routine ``/fire``
EFFECT leg) is deliberately NOT ported in this slice: the config family is
DORMANT posture (inert unless keyed) and the transmit lane would be a new
egress adapter — the handlers hold an honest pending terminal there.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sb.kernel.config import Config

__all__ = [
    "MISSING_CONFIG_HELP",
    "bridge_configured",
    "install_hermes_bridge_config",
    "reset_for_tests",
]

# disbot/cogs/hermes_cog.py `_MISSING_TOKEN_HELP`, byte-for-byte (the
# parity goldens pin this as the unconfigured-bridge embed description).
MISSING_CONFIG_HELP = (
    "The Hermes→Claude dispatch bridge is not configured.\n\n"
    "Set these env vars on Railway (or in `.env` locally):\n"
    "```\n"
    "CLAUDE_ROUTINE_FIRE_URL=https://api.anthropic.com/v1/claude_code/routines/<id>/fire\n"
    "CLAUDE_ROUTINE_TOKEN=sk-ant-oat01-…\n"
    "CLAUDE_ROUTINE_BETA=experimental-cc-routine-2026-04-01\n"
    "CLAUDE_ROUTINE_VERSION=2023-06-01\n"
    "```\n"
    "See `docs/operations/hermes-dispatch-bridge.md` for the full setup runbook."
)

_fire_url: str = ""
_token_present: bool = False
_installed: bool = False


def install_hermes_bridge_config(cfg: "Config") -> None:
    """Boot seam: record the bridge endpoint + token PRESENCE (never the
    secret value — the ``install_secret_presence`` posture)."""
    global _fire_url, _token_present, _installed
    _fire_url = str(getattr(cfg, "CLAUDE_ROUTINE_FIRE_URL", "") or "")
    probe = getattr(cfg, "is_configured", None)
    _token_present = bool(callable(probe) and probe("CLAUDE_ROUTINE_TOKEN"))
    _installed = True


def bridge_configured() -> bool:
    """The shipped missing_config gate: URL AND token, else unconfigured.
    Uninstalled fails closed (parity harness / partial boots)."""
    return _installed and bool(_fire_url) and _token_present


def reset_for_tests() -> None:
    global _fire_url, _token_present, _installed
    _fire_url = ""
    _token_present = False
    _installed = False

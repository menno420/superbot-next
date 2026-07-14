"""Live render forwarding — the idle-engine views the host renders (PLUG-001, inc2).

This module is deliberately **sb-free**: it imports only ``idle_engine.render``
(the pure, platform-free embed layer) and the stdlib. The manifest
(``superbot_idle_plugin.manifest``) imports these forwarders and registers them
as ``@handler`` refs, but the forwarding logic itself never touches ``sb`` — so
idle's sb-free CI can exercise the real forwarding path directly (a NON-gated
test), proving the seam works rather than merely importing it.

The contract seam (``docs/game-plugin-contract.md`` @ ``d3dba9b``): the host
dispatches a command to a registered ``@handler`` callable and injects the
subsystem's state. The engine's render layer
(:mod:`idle_engine.render`) already returns plain embed-shaped dicts
(``title`` / ``description`` / ``color`` int / ``fields``) validated against the
platform caps, so the adapter's whole job is to FORWARD them VERBATIM — zero
formatting, zero re-shaping. Each forwarder here is one line over
``idle_engine.render``.

Host-validated boundary: the EXACT signature the host calls a handler with (how
it injects the idle instance's ``GameState`` + resolved ``Theme`` + ``now``) is
a host-side detail of ``sb/app/plugin_host.py`` and is validated against a live
host, not in idle CI. The forwarders are therefore typed against a small,
explicit :class:`IdleRenderState` handle — the host adapter constructs it (or an
equivalent) and calls the forwarder; idle CI proves the forwarding is
byte-identical to ``idle_engine.render``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from idle_engine.render import render_prestige, render_shop, render_status

if TYPE_CHECKING:  # type-only imports — keeps this module runtime-light
    from idle_engine.state import GameState
    from idle_engine.theme import Theme


@dataclass(frozen=True)
class IdleRenderState:
    """The host-provided state handle a render forwarder needs.

    A thin, explicit container the host adapter fills from the idle instance
    it loaded (the ``GameState`` off the host store + the resolved ``Theme``
    pack + the caller's unix ``now``). The engine takes state IN and hands an
    embed dict BACK — this handle is exactly the ``(state, theme, now)`` the
    render layer's signatures require, named so the host wiring is legible.
    """

    game_state: GameState
    theme: Theme
    now: int = 0


def forward_status(state: IdleRenderState) -> dict:
    """Forward :func:`idle_engine.render.render_status` output VERBATIM.

    The status view: balances, generator counts + rates, offline gains
    displayed since ``last_seen`` up to ``state.now``.
    """
    return render_status(state.game_state, state.theme, state.now)


def forward_shop(state: IdleRenderState) -> dict | None:
    """Forward :func:`idle_engine.render.render_shop` output VERBATIM.

    Returns ``None`` when the pack declares no ``upgrades`` block (the engine's
    own contract — the adapter forwards that too, never inventing a view).
    """
    return render_shop(state.game_state, state.theme)


def forward_prestige(state: IdleRenderState) -> dict | None:
    """Forward :func:`idle_engine.render.render_prestige` output VERBATIM.

    Returns ``None`` when the pack declares no ``prestige`` block.
    """
    return render_prestige(state.game_state, state.theme)

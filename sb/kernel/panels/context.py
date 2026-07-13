"""``PanelContext`` — the engine's runtime argument to every provider and
handler (design-spec §2.3). Constructed ONLY by the kernel; handlers never
touch a raw ``discord.Interaction`` (this replaces the ``help_ctx_shim``).
Carries the L-24 ``LocaleContext`` for the render/copy seam.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Mapping

from sb.kernel.interaction.locale import LocaleContext
from sb.kernel.interaction.request import ActorRef
from sb.spec.panels import Audience

__all__ = ["PanelContext", "PanelOrigin"]


class PanelOrigin(enum.Enum):
    INTERACTION = "interaction"
    ANCHOR = "anchor"


@dataclass(frozen=True)
class PanelContext:
    bot: object | None                 # opaque gateway handle (adapters own the type)
    guild_id: int | None
    actor: ActorRef
    channel_id: int | None
    origin: PanelOrigin
    audience: Audience
    locale: LocaleContext = LocaleContext()
    #: the opening request's args (read-only) — session-lifecycle game
    #: views render request-parameterized copy (the shipped quick-play
    #: bet line); grammar panels may ignore it.
    params: Mapping[str, object] = field(default_factory=dict)
    #: the opening request's ingress surface value ("prefix"/"slash"/
    #: "component"/…, None when the caller has no request) — surface-keyed
    #: rendering for renderer overrides (the shipped panel-manager
    #: back-to-help hook appended its button on the MESSAGE path only;
    #: goldens/server_management's prefix vs slash sweeps pin the
    #: split). Read-only, engine-set; grammar panels may ignore it.
    surface: str | None = None

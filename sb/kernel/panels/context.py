"""``PanelContext`` — the engine's runtime argument to every provider and
handler (design-spec §2.3). Constructed ONLY by the kernel; handlers never
touch a raw ``discord.Interaction`` (this replaces the ``help_ctx_shim``).
Carries the L-24 ``LocaleContext`` for the render/copy seam.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

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

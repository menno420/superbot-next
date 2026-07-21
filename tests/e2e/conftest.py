"""In-process e2e adapter test tier (D5.1 — discord-installed variant).

The *non-replay twin* of the golden-parity harness. Golden-parity boots the
new bot in-process and drives it through a fake-HTTP/gateway transport that
SUBSTITUTES for the whole discord adapter (`ParityPresenter`,
`ParityChannelEmitter`, ... — `sb/adapters/parity/boot.py`), so the ~19 real
`sb/adapters/discord/*` modules are byte-invisible to every golden (the D5 doc's
P1 blind spot: `docs/design/D5-e2e-test-harness.md`). This tier closes that gap
without duplicating parity: it rides the SAME in-process boot + real Postgres
(reusing `tests/integration/conftest.py:boot_harness`) but **re-points the panel
presenter and channel emitter at the REAL discord adapter** — `build_embed` /
`build_view` (`panel_view.py`) and `DiscordChannelEmitter` (`egress.py`) — over
recording fakes, so a real command is driven end-to-end through real
`discord`/`app_commands`/`ui` types and the materialized egress is asserted.

Hermetic — no LIVE gateway/token/network (only the D5.2 LIVE tier is
owner-gated). It needs `discord` installed AND a reachable Postgres, exactly the
`golden-parity` CI job's environment (the hash-pinned lock ships
`discord-py==2.7.1` and the job runs a Postgres service). Where either is
absent — the hermetic `code-quality` gate installs no runtime deps — every test
here SKIPS cleanly (never fails), the guarded-absence discipline the integration
tier already uses.

NOTE: like `tests/integration/`, every test drives its ENTIRE body (boot, work,
close) through ONE `asyncio.run()` — asyncpg pools bind to the creating loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest

try:
    import discord  # noqa: F401 — presence probe only, see DISCORD_AVAILABLE
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False

# Reuse the integration tier's real-Postgres boot machinery verbatim (the D5.1
# design: "reuse tests/integration/conftest.py's machinery, don't duplicate").
# boot_harness() = Harness.start(require_db=True) + a truncated-fresh schema,
# skipping (not failing) without asyncpg/Postgres.
from tests.integration.conftest import boot_harness


@dataclass
class PanelCapture:
    """One real-adapter panel materialization: the kernel RenderedPanel plus
    the REAL discord objects `panel_view.py` built from it."""

    panel_id: str
    embed: Any            # discord.Embed | None
    view: Any             # sb.adapters.discord.panel_view.PanelRuntimeView
    rendered: Any


@dataclass
class SendCapture:
    """One real `channel.send(...)` the DiscordChannelEmitter / poster made."""

    channel_id: int
    args: tuple
    kwargs: dict


class _RecordingChannel:
    """A fake discord text channel: records `channel.send(...)` and mints a
    message id, the sink the real `DiscordChannelEmitter` writes into."""

    def __init__(self, channel_id: int, recorder: "RealAdapterRecorder") -> None:
        self.id = int(channel_id)
        self._recorder = recorder

    async def send(self, *args: Any, **kwargs: Any) -> Any:
        self._recorder.sends.append(
            SendCapture(channel_id=self.id, args=args, kwargs=kwargs))
        return SimpleNamespace(id=self._recorder._next_id())


class _RecordingBot:
    """Ducks the `get_channel`/`fetch_channel` the DiscordChannelEmitter and the
    panel poster call — every id resolves to a memoized recording channel."""

    def __init__(self, recorder: "RealAdapterRecorder") -> None:
        self._recorder = recorder
        self._channels: dict[int, _RecordingChannel] = {}

    def get_channel(self, channel_id: int) -> _RecordingChannel:
        return self._channels.setdefault(
            int(channel_id), _RecordingChannel(channel_id, self._recorder))

    async def fetch_channel(self, channel_id: int) -> _RecordingChannel:
        return self.get_channel(channel_id)


@dataclass
class RealAdapterRecorder:
    """Swaps the parity capture seams for the REAL discord adapter and records
    what it materialized. `install()` re-points:

      * the panel-engine presenter → the real `panel_view.build_embed` /
        `build_view` (real `discord.Embed` / `discord.ui.View` construction).
      * the kernel channel emitter → the real `DiscordChannelEmitter` over a
        recording bot (real `allowed_mentions_for` + `discord.AllowedMentions`).
    """

    panels: list[PanelCapture] = field(default_factory=list)
    sends: list[SendCapture] = field(default_factory=list)
    _id: int = 950_000_000_000_000_000

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def install(self) -> "RealAdapterRecorder":
        from sb.adapters.discord import panel_view
        from sb.adapters.discord.egress import DiscordChannelEmitter
        from sb.kernel.interaction.egress import install_channel_emitter
        from sb.kernel.panels import engine as panel_engine

        recorder = self

        class _RecordingRealPresenter:
            """Drives the REAL panel_view.py materialization from the live
            command's RenderedPanel and records the real discord objects."""

            async def __call__(self, rendered: Any, req: Any) -> object:
                capture = PanelCapture(
                    panel_id=str(getattr(rendered, "panel_id", "")),
                    embed=panel_view.build_embed(rendered),
                    view=panel_view.build_view(rendered),
                    rendered=rendered)
                recorder.panels.append(capture)
                return recorder._next_id()

        panel_engine.install_panel_presenter(_RecordingRealPresenter())
        install_channel_emitter(DiscordChannelEmitter(_RecordingBot(self)))
        return self

    # -- assertion helpers -------------------------------------------------

    def panel(self, panel_id: str) -> PanelCapture:
        """The first captured materialization of `panel_id` (fails loudly if
        the command never rendered it — a real regression signal)."""
        for cap in self.panels:
            if cap.panel_id == panel_id:
                return cap
        raise AssertionError(
            f"panel {panel_id!r} was never rendered through the real adapter; "
            f"saw {[c.panel_id for c in self.panels]}")


async def boot_e2e_harness() -> tuple[Any, RealAdapterRecorder]:
    """Boot the in-process e2e harness (real bot + real Postgres) with the real
    discord adapter wired in. Returns `(harness, recorder)`. SKIPS (never fails)
    when `discord` is absent; `boot_harness()` itself skips without asyncpg/
    Postgres. Caller awaits `harness.close()`."""
    if not DISCORD_AVAILABLE:
        pytest.skip("discord not installed — the D5.1 discord-installed e2e "
                    "tier needs the full runtime lock (requirements.lock); it "
                    "runs in the golden-parity CI job's environment")

    harness = await boot_harness()
    recorder = RealAdapterRecorder().install()
    return harness, recorder

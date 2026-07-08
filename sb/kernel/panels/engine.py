"""The panel ENGINE (K8/S9b) — the ``install_panel_engine`` target.

One kernel runtime interprets every grammar-expressible ``PanelSpec``
(design-spec §2.3): invoker-lock, timeout-disable, standard nav, page-turn,
persistence semantics — no per-panel view class. The discord adapter is a
thin PRESENTER port (``install_panel_presenter``): the engine renders the
pure ``RenderedPanel`` model; the adapter materializes + sends it.

Navigation clicks are re-resolved at click time (§2.4): parents/hubs are
rebuilt FRESH from the registry — never captured; the panel a nav id names
is looked up when the click happens, so home routing follows arrangement.

Escape hatches (§2.9): ``renderer_override`` (tier-2) and ``legacy_view``
(tier-3) bypass the grammar renderer through their REGISTERED refs — both
still enter through this engine (the audited seam), never around it.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from sb.kernel.interaction.locale import LocaleContext
from sb.kernel.interaction.request import ResolveRequest
from sb.kernel.panels.context import PanelContext, PanelOrigin
from sb.kernel.panels.registry import NavBinding, get_panel, hub_panel_id
from sb.kernel.panels.render import RenderedPanel, render_panel
from sb.spec.panels import PanelSpec
from sb.spec.refs import PanelRef, resolve as resolve_ref

logger = logging.getLogger("sb.kernel.panels.engine")

__all__ = [
    "PanelPresenterNotInstalled",
    "PanelSession",
    "handle_nav",
    "install_panel_presenter",
    "may_interact",
    "open_panel",
    "reset_panel_engine_for_tests",
    "session_for",
]


class PanelPresenterNotInstalled(RuntimeError):
    """No presenter installed — classified as a BUG envelope by resolve()."""


# --- presenter port -------------------------------------------------------------

# present(rendered, req) — send or edit the surface-native message.
PanelPresenter = Callable[[RenderedPanel, ResolveRequest], Awaitable[object]]


async def _no_presenter(rendered: RenderedPanel, req: ResolveRequest) -> object:
    raise PanelPresenterNotInstalled(
        f"panel presenter not installed: cannot present {rendered.panel_id!r} "
        f"(composition root installs the discord adapter's presenter)")


_presenter: PanelPresenter = _no_presenter


def install_panel_presenter(presenter: PanelPresenter) -> None:
    global _presenter
    _presenter = presenter


# --- sessions (in-memory; PERSISTENT panels are restart-safe BY custom_id — the
# static table re-binds their components with no session at all) ----------------

@dataclass
class PanelSession:
    panel_id: str
    invoker_id: int | None            # None = not invoker-locked
    audience: str
    page: int = 0
    opened_at: float = field(default_factory=time.monotonic)
    timeout_s: int | None = 180
    message_ref: object = None        # opaque adapter handle

    @property
    def expired(self) -> bool:
        if self.timeout_s is None:
            return False
        return (time.monotonic() - self.opened_at) > self.timeout_s


_sessions: dict[str, PanelSession] = {}     # keyed by an opaque message key
_SESSIONS_MAX = 2048


def session_for(message_key: str) -> PanelSession | None:
    return _sessions.get(message_key)


def _store_session(message_key: str, session: PanelSession) -> None:
    _sessions[message_key] = session
    while len(_sessions) > _SESSIONS_MAX:
        _sessions.pop(next(iter(_sessions)))


def may_interact(session: PanelSession | None, user_id: int | None) -> bool:
    """The invoker lock (audience=invoker ⇒ only the opener may click).
    No session (e.g. a persistent panel after restart) ⇒ open access —
    authority is still re-resolved per click by resolve()."""
    if session is None or session.invoker_id is None:
        return True
    return session.invoker_id == user_id


def reset_panel_engine_for_tests() -> None:
    global _presenter
    _presenter = _no_presenter
    _sessions.clear()


# --- the engine entrypoints -----------------------------------------------------

def _context_from_request(spec: PanelSpec, req: ResolveRequest) -> PanelContext:
    return PanelContext(
        bot=None, guild_id=req.guild_id, actor=req.actor,
        channel_id=req.channel_id, origin=PanelOrigin.INTERACTION,
        audience=spec.audience, locale=LocaleContext())


async def _render_and_present(spec: PanelSpec, req: ResolveRequest, *,
                              page: int = 0) -> None:
    ctx = _context_from_request(spec, req)
    if spec.renderer_override is not None:
        # tier-2 escape hatch: a registered renderer produces the RenderedPanel.
        rendered = await resolve_ref(spec.renderer_override)(spec, ctx)
    elif spec.legacy_view is not None:
        # tier-3 contingency lane: the re-homed view renders itself through
        # the presenter-native path; the registered callable owns the send.
        await resolve_ref(spec.legacy_view)(spec, ctx, req)
        return
    else:
        rendered = await render_panel(spec, ctx, page=page)
    message_ref = await _presenter(rendered, req)
    key = str(message_ref) if message_ref is not None else req.request_id
    _store_session(key, PanelSession(
        panel_id=spec.panel_id, invoker_id=rendered.invoker_lock,
        audience=rendered.audience, page=page, timeout_s=rendered.timeout_s,
        message_ref=message_ref))


async def open_panel(ref: PanelRef, req: ResolveRequest) -> None:
    """THE `install_panel_engine` target — resolve()'s OPEN_PANEL terminal."""
    spec = get_panel(ref.name)
    await _render_and_present(spec, req)


async def handle_nav(binding: NavBinding, req: ResolveRequest) -> None:
    """Dispatch an engine-injected nav slot: help / hub-home / back / page.
    Every route re-resolves through the registry AT CLICK TIME — parents are
    rebuilt fresh, never captured (§2.4)."""
    if binding.kind == "help":
        target = hub_panel_id("help") or "help.home"
        await _render_and_present(get_panel(target), req)
    elif binding.kind == "hub":
        target = hub_panel_id(binding.target)
        if target is None:
            raise LookupError(f"hub {binding.target!r} has no registered hub panel")
        await _render_and_present(get_panel(target), req)
    elif binding.kind == "back":
        await _render_and_present(get_panel(binding.target), req)
    elif binding.kind == "page":
        panel_id, _, page = binding.target.rpartition(":")
        await _render_and_present(get_panel(panel_id), req, page=int(page))
    else:  # pragma: no cover — the registry mints only the four kinds
        raise ValueError(f"unknown nav binding kind {binding.kind!r}")

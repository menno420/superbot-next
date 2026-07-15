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
import secrets
import time
from dataclasses import dataclass, field, replace as _dc_replace
from typing import Awaitable, Callable

from sb.kernel.interaction.locale import LocaleContext
from sb.kernel.interaction.request import ResolveRequest, Surface
from sb.kernel.panels.context import PanelContext, PanelOrigin
from sb.kernel.panels.registry import NavBinding, get_panel, hub_panel_id
from sb.kernel.panels.render import RenderedPanel, render_panel
from sb.spec.panels import PanelSpec
from sb.spec.refs import PanelRef, resolve as resolve_ref

logger = logging.getLogger("sb.kernel.panels.engine")

__all__ = [
    "EDIT_EDITED",
    "EDIT_FAILED",
    "EDIT_MISSING",
    "EDIT_UNAVAILABLE",
    "EphemeralComponent",
    "PanelPresenterNotInstalled",
    "PanelSession",
    "edit_anchored_panel",
    "ephemeral_route",
    "handle_nav",
    "install_panel_anchor_store",
    "install_panel_message_editor",
    "install_panel_message_poster",
    "install_panel_presenter",
    "may_interact",
    "open_panel",
    "post_anchored_panel",
    "push_session_refresh",
    "refresh_session_view",
    "register_confirm_session",
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


# --- message-editor port (the on-ready resume sweep's edit lane) ----------------
#
# The oracle's ``on_ready`` sweeps edited persisted panel messages in place
# (``channel.fetch_message`` → ``message.edit`` — setup_cog._resume_one_launcher
# / essential_setup.revive_one_essential_flow). At boot there is no live
# interaction origin and no PanelSession, so the presenter port cannot carry
# the edit; this dedicated port takes a kernel-rendered panel plus the
# PERSISTED (channel_id, message_id) pair. The discord adapter implements it
# (sb/adapters/discord/panel_view.DiscordPanelMessageEditor); uninstalled it
# answers EDIT_UNAVAILABLE (headless/CI — never a crash).

#: the edit was applied.
EDIT_EDITED = "edited"
#: the message is GONE (the oracle ``discord.NotFound`` branch) — callers may
#: clear their persisted pointer so the sweep stops retrying it.
EDIT_MISSING = "missing"
#: the edit could not be applied (channel uncached / forbidden / HTTP error —
#: the oracle's log-and-skip branches, folded).
EDIT_FAILED = "failed"
#: no editor installed (headless composition — the sweep degrades to a no-op).
EDIT_UNAVAILABLE = "unavailable"

# editor(rendered, *, channel_id, message_id) -> EDIT_EDITED|EDIT_MISSING|EDIT_FAILED
_message_editor = None


def install_panel_message_editor(editor) -> None:
    global _message_editor
    _message_editor = editor


async def edit_anchored_panel(ref: PanelRef, *, guild_id: int | None,
                              channel_id: int, message_id: int,
                              actor, params: dict | None = None) -> str:
    """Re-render panel *ref* fresh and edit it onto the persisted channel
    message (the boot-time twin of ``refresh_session_view`` — no live
    session required). Returns one of the ``EDIT_*`` outcomes.

    Component ids are NOT session-minted here: a boot edit re-binds only
    components whose wire ids are static (``custom_id_override`` /
    persistent panels) — exactly the oracle's persistent-view doctrine
    (the rebound message keeps working because custom ids never change).
    Renderers see ``PanelOrigin.ANCHOR`` with the caller's *actor* (the
    sweep passes a system actor)."""
    if _message_editor is None:
        return EDIT_UNAVAILABLE
    spec = get_panel(ref.name)
    ctx = PanelContext(
        bot=None, guild_id=guild_id, actor=actor,
        channel_id=channel_id, origin=PanelOrigin.ANCHOR,
        audience=spec.audience, locale=LocaleContext(),
        params=dict(params or {}), surface=None)
    if spec.renderer_override is not None:
        rendered = await resolve_ref(spec.renderer_override)(spec, ctx)
    else:
        rendered = await render_panel(spec, ctx)
    return await _message_editor(rendered, channel_id=int(channel_id),
                                 message_id=int(message_id))


# --- message-poster port (the on-guild-join launcher's post lane) ---------------
#
# The oracle's ``on_guild_join`` posted the setup launcher into a chosen
# channel (``channel.send(embed=..., view=...)`` — setup_cog
# ``_post_launcher_in_setup_channel`` / launcher.post_launcher). At a
# gateway event there is no live interaction origin, so the presenter port
# cannot carry the send; this dedicated port — the message-editor port's
# POST twin — takes a kernel-rendered panel plus the target channel id and
# answers the minted message id. The discord adapter implements it
# (sb/adapters/discord/panel_view.DiscordPanelMessagePoster); uninstalled
# it answers None (headless/CI — the callers' counted no-op, never a
# crash).

# poster(rendered, *, channel_id, mention_user_ids) -> message_id | None
_message_poster = None


def install_panel_message_poster(poster) -> None:
    global _message_poster
    _message_poster = poster


async def post_anchored_panel(ref: PanelRef, *, guild_id: int | None,
                              channel_id: int, actor,
                              params: dict | None = None,
                              mention_user_ids: tuple[int, ...] = ()
                              ) -> int | None:
    """Render panel *ref* fresh and POST it into *channel_id* (the
    event-time twin of ``edit_anchored_panel`` — no live interaction
    required). Returns the minted message id, or None when no poster is
    installed / the send could not be applied.

    Component ids are NOT session-minted here: an event-time post binds
    only components whose wire ids are static (``custom_id_override`` /
    persistent panels) — exactly the oracle's persistent-view doctrine.
    Renderers see ``PanelOrigin.ANCHOR`` with the caller's *actor*.
    ``mention_user_ids`` is the send's explicit user-mention allowlist
    (the oracle's owner-ping ``AllowedMentions(users=True,
    everyone=False)`` — default-deny stands: empty means no pings)."""
    if _message_poster is None:
        return None
    spec = get_panel(ref.name)
    ctx = PanelContext(
        bot=None, guild_id=guild_id, actor=actor,
        channel_id=channel_id, origin=PanelOrigin.ANCHOR,
        audience=spec.audience, locale=LocaleContext(),
        params=dict(params or {}), surface=None)
    if spec.renderer_override is not None:
        rendered = await resolve_ref(spec.renderer_override)(spec, ctx)
    else:
        rendered = await render_panel(spec, ctx)
    message_id = await _message_poster(
        rendered, channel_id=int(channel_id),
        mention_user_ids=tuple(int(u) for u in mention_user_ids))
    return int(message_id) if message_id is not None else None


# --- anchor-store port (the shipped panel_anchors registry) ---------------------

# Channel-sent panel messages are recorded so later refresh/stale-marking can
# find them (sb.kernel.panels.anchors is the Postgres implementation);
# ephemeral interaction responses are never anchored — no editable channel
# message exists. Uninstalled port = no-op (DB-free environments).
_anchor_store = None

#: interaction surfaces present through an interaction response (no channel
#: message id the bot could re-fetch) — never anchored; the message surfaces
#: (PREFIX, MAINTENANCE, SETUP) send real channel messages.
_INTERACTION_SURFACES = frozenset({
    Surface.SLASH, Surface.COMPONENT, Surface.MODAL,
    Surface.NL_INTENT, Surface.NL_ORCHESTRATION,
})


def install_panel_anchor_store(store) -> None:
    global _anchor_store
    _anchor_store = store


async def _record_anchor(spec: PanelSpec, req: ResolveRequest,
                         message_ref: object) -> None:
    if _anchor_store is None or message_ref is None:
        return
    if req.surface in _INTERACTION_SURFACES:
        return
    if spec.session_lifecycle:
        # the shipped registry (utils/db/anchors.py) held panel-MANAGER
        # panels only; timeout-bound session views (the shipped
        # LeaderboardView class) were never anchored — the leaderboard
        # golden pins the no-anchor-row delta.
        return
    try:
        message_id = int(str(message_ref))
    except (TypeError, ValueError):
        return              # opaque non-message handle — nothing to anchor
    try:
        await _anchor_store(
            guild_id=req.guild_id, channel_id=req.channel_id,
            message_id=message_id, subsystem=spec.subsystem,
            user_id=req.actor.user_id)
    except Exception:  # noqa: BLE001 — anchoring never takes the panel down
        logger.warning("panel anchor write failed for %s", spec.panel_id,
                       exc_info=True)


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
    # session-lifecycle panels: component_id -> the minted 32-hex custom_id
    # (a refresh re-renders onto the SAME wire ids — the shipped views kept
    # their auto-ids across edits).
    component_ids: dict = field(default_factory=dict)
    # the channel the session message lives in — what an interaction-free
    # push edit (``push_session_refresh``) hands the ``_message_editor``
    # port; None for sessions minted outside a channel (confirm surfaces,
    # request-id-keyed fallbacks).
    channel_id: int | None = None

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


def register_confirm_session(message_key: str, *, invoker_id: int | None,
                             timeout_s: int | None) -> None:
    """Invoker-lock a CONFIRM surface message (02 §3.2 — the confirm view is
    a session-scoped kernel view): the live component feed mirrors
    ``may_interact`` for every component click, so registering the confirm
    message here locks BOTH the view path and the feed path through the one
    seam. panel_id is the reserved confirm surface marker, not a registry
    panel."""
    _store_session(message_key, PanelSession(
        panel_id="sb.confirm", invoker_id=invoker_id, audience="invoker",
        timeout_s=timeout_s))


def may_interact(session: PanelSession | None, user_id: int | None) -> bool:
    """The invoker lock (audience=invoker ⇒ only the opener may click).
    No session (e.g. a persistent panel after restart) ⇒ open access —
    authority is still re-resolved per click by resolve()."""
    if session is None or session.invoker_id is None:
        return True
    return session.invoker_id == user_id


# --- session-lifecycle game views (the shipped discord.py view semantics) -------
#
# A ``session_lifecycle=True`` panel is the shipped ephemeral game VIEW made
# declarative: its components get RUN-MINTED custom ids (32-hex — byte-for-
# byte the auto-id shape discord.py minted for the shipped views, which the
# parity Normalizer symbolizes as <cid:N>), bound IN MEMORY to the declared
# component spec plus the opening request's args. The binding dies with the
# process/timeout — a stale click falls through to the §3.4 polite-expiry
# terminal, exactly the shipped views' after-restart behavior. Session views
# are never anchored (panel_anchors is the refreshable-panel registry; the
# shipped game views were not in it).

@dataclass(frozen=True)
class EphemeralComponent:
    """One minted session-view component binding."""

    panel_id: str
    component_id: str
    spec: object                      # the declared PanelActionSpec | SelectorSpec
    args: dict
    invoker_id: int | None
    opened_at: float = field(default_factory=time.monotonic)
    timeout_s: int | None = 180

    @property
    def expired(self) -> bool:
        if self.timeout_s is None:
            return False
        return (time.monotonic() - self.opened_at) > self.timeout_s


_ephemeral: dict[str, EphemeralComponent] = {}
_EPHEMERAL_MAX = 4096


def ephemeral_route(custom_id: str) -> EphemeralComponent | None:
    """The component adapter's session-view lookup — None for unknown or
    expired ids (the caller falls through to the polite-expiry terminal)."""
    binding = _ephemeral.get(custom_id)
    if binding is None:
        return None
    if binding.expired:
        _ephemeral.pop(custom_id, None)
        return None
    return binding


def _mint_ephemeral(spec: PanelSpec, rendered: RenderedPanel,
                    req: ResolveRequest) -> RenderedPanel:
    """Rewrite a session-lifecycle panel's DECLARED components onto minted
    32-hex ids and store their bindings; engine-injected nav slots (if any)
    keep their static ids. A ``custom_id_override`` component keeps its
    VERBATIM id too — the legacy pin survives even inside a session view
    (the shipped timeout views mixed auto-ids with explicit persistent
    child-forwarding ids, e.g. utility_cog's ``utility:open:<child>``
    buttons — goldens/utility/sweep_utilitymenu pins the mix); it stays
    routable through the ONE static table."""
    by_canonical: dict[str, tuple[str, object]] = {}
    for comp in tuple(spec.actions) + tuple(spec.selectors):
        if getattr(comp, "custom_id_override", ""):
            continue                       # verbatim pin — never re-minted
        comp_id = (getattr(comp, "action_id", "")
                   or getattr(comp, "selector_id", ""))
        by_canonical[f"{spec.panel_id}.{comp_id}"] = (comp_id, comp)
    out = []
    for component in rendered.components:
        bound = by_canonical.get(component.custom_id)
        if bound is None:
            out.append(component)
            continue
        comp_id, cspec = bound
        minted = secrets.token_hex(16)
        _ephemeral[minted] = EphemeralComponent(
            panel_id=spec.panel_id, component_id=comp_id, spec=cspec,
            args={**dict(req.args), "session_action": comp_id},
            invoker_id=rendered.invoker_lock, timeout_s=rendered.timeout_s)
        out.append(_dc_replace(component, custom_id=minted))
    while len(_ephemeral) > _EPHEMERAL_MAX:
        _ephemeral.pop(next(iter(_ephemeral)))
    return _dc_replace(rendered, components=tuple(out))


def reset_panel_engine_for_tests() -> None:
    global _presenter, _anchor_store, _message_editor, _message_poster
    _presenter = _no_presenter
    _anchor_store = None
    _message_editor = None
    _message_poster = None
    _sessions.clear()
    _ephemeral.clear()


# --- the engine entrypoints -----------------------------------------------------

def _context_from_request(spec: PanelSpec, req: ResolveRequest) -> PanelContext:
    return PanelContext(
        bot=None, guild_id=req.guild_id, actor=req.actor,
        channel_id=req.channel_id, origin=PanelOrigin.INTERACTION,
        audience=spec.audience, locale=LocaleContext(),
        params=dict(req.args or {}),
        surface=getattr(req.surface, "value", None))


async def _render_and_present(spec: PanelSpec, req: ResolveRequest, *,
                              page: int = 0, browse=None,
                              window=None) -> str:
    ctx = _context_from_request(spec, req)
    if window is not None:
        # windowed-select position: rides the reserved ctx.params key so it
        # reaches render_panel through EVERY render path — the grammar
        # renderer's fallback AND a renderer_override that re-calls
        # ``render_panel(spec, ctx)`` itself (the cog_routing detail).
        from sb.kernel.panels import selectwindow

        ctx.params[selectwindow.WINDOW_PARAM] = window
    if spec.renderer_override is not None:
        # tier-2 escape hatch: a registered renderer produces the RenderedPanel.
        rendered = await resolve_ref(spec.renderer_override)(spec, ctx)
    elif spec.legacy_view is not None:
        # tier-3 contingency lane: the re-homed view renders itself through
        # the presenter-native path; the registered callable owns the send.
        await resolve_ref(spec.legacy_view)(spec, ctx, req)
        return req.request_id
    else:
        # ``browse`` arms the shared BrowserView engine (D-0034) for the named
        # block — data re-resolved fresh at click time (§2.4), like every nav.
        # On a fresh OPEN / nav-back (browse is None) a surface that DECLARES a
        # browse algebra auto-arms its default browse state, so its interactive
        # sort/filter/page controls are live from the very first render; a
        # control click carries its own explicit BrowseState via _handle_browse
        # and skips this default. A panel with no browsable block yields None —
        # the byte-identical static render.
        if browse is None:
            from sb.kernel.panels import browserview

            browse = browserview.default_browse_state(spec)
        rendered = await render_panel(spec, ctx, page=page, browse=browse)
    minted_ids: dict[str, str] = {}
    if spec.session_lifecycle:
        rendered = _mint_ephemeral(spec, rendered, req)
        minted_ids = {
            _ephemeral[c.custom_id].component_id: c.custom_id
            for c in rendered.components if c.custom_id in _ephemeral}
    message_ref = await _presenter(rendered, req)
    key = str(message_ref) if message_ref is not None else req.request_id
    _store_session(key, PanelSession(
        panel_id=spec.panel_id, invoker_id=rendered.invoker_lock,
        audience=rendered.audience, page=page, timeout_s=rendered.timeout_s,
        message_ref=message_ref, component_ids=minted_ids,
        channel_id=(int(req.channel_id)
                    if req.channel_id is not None else None)))
    if not spec.session_lifecycle:
        # session views are never anchored — no refreshable channel panel
        # exists (the shipped game views were not in panel_anchors).
        await _record_anchor(spec, req, message_ref)
    return key


async def open_panel(ref: PanelRef, req: ResolveRequest) -> str:
    """THE `install_panel_engine` target — resolve()'s OPEN_PANEL terminal.
    Returns the stored session's message key so an opening handler can drive
    a follow-up ``refresh_session_view`` (the shipped send-then-edit flows,
    e.g. utility_cog's ``!ping`` round-trip edit); terminal callers ignore
    it."""
    spec = get_panel(ref.name)
    return await _render_and_present(spec, req)


async def refresh_session_view(req: ResolveRequest, *, message_key: str,
                               params: dict, expire: bool = False) -> bool:
    """Re-render a live session view IN PLACE (the shipped game views'
    ``interaction.response.defer()`` + ``message.edit`` loop): render the
    session's panel with *params*, rewrite the declared components back
    onto the ORIGINAL minted ids (never re-mint — the wire ids are stable
    across edits), and present with ``edit_message_ref`` set so the
    presenter edits instead of sending. ``expire=True`` tears the session
    down after the edit (terminal result: the shipped ``view.stop()`` —
    later clicks fall to the polite-expiry terminal).

    Returns False when no live session exists for *message_key* (process
    restart / eviction) — the caller degrades to its text reply."""
    session = _sessions.get(message_key)
    if session is None or session.expired:
        return False
    spec = get_panel(session.panel_id)
    ctx = _context_from_request(spec, req)
    ctx.params.clear()
    ctx.params.update(params)
    rendered = await _render_session_panel(spec, session, ctx)
    rendered = _dc_replace(rendered,
                           edit_message_ref=session.message_ref)
    await _presenter(rendered, req)
    if expire:
        _expire_session(message_key, session)
    return True


async def _render_session_panel(spec: PanelSpec, session: PanelSession,
                                ctx: PanelContext) -> RenderedPanel:
    """Re-render *spec* for a live session and rewrite the declared
    components back onto the session's ORIGINAL minted ids (never re-mint
    — the wire ids are stable across edits; the shipped views kept their
    auto-ids). Shared by the interaction refresh and the push edit."""
    if spec.renderer_override is not None:
        rendered = await resolve_ref(spec.renderer_override)(spec, ctx)
    else:
        rendered = await render_panel(spec, ctx, page=session.page)
    remapped = []
    for component in rendered.components:
        for comp_id, minted in session.component_ids.items():
            if component.custom_id == f"{spec.panel_id}.{comp_id}":
                component = _dc_replace(component, custom_id=minted)
                break
        remapped.append(component)
    return _dc_replace(rendered, components=tuple(remapped))


def _expire_session(message_key: str, session: PanelSession) -> None:
    """Tear a session down after a terminal edit (the shipped
    ``view.stop()`` — later clicks fall to the polite-expiry terminal)."""
    for minted in session.component_ids.values():
        _ephemeral.pop(minted, None)
    _sessions.pop(message_key, None)


async def push_session_refresh(message_key: str, *, params: dict,
                               actor, guild_id: int | None = None,
                               expire: bool = False) -> str:
    """Re-render a live session view IN PLACE with NO interaction — the
    real-time twin of :func:`refresh_session_view` (docs/decisions.md
    D-0090): same render-onto-the-ORIGINAL-minted-ids body, but the edit
    rides the ``_message_editor`` port (the boot-sweep lane) instead of
    the presenter, so a background task (the fishing bite timer) can
    announce state onto the session message the way the oracle's
    ``message.edit`` background edits did. Returns one of the ``EDIT_*``
    outcomes: no editor installed ⇒ ``EDIT_UNAVAILABLE`` (headless/CI —
    the sweep's degradation posture, never a crash); no live session /
    no editable channel message ⇒ ``EDIT_MISSING`` (process restart or
    eviction — the caller degrades exactly as the shipped game views'
    message-gone edits did). Renderers see ``PanelOrigin.ANCHOR`` (no
    live interaction origin — the ``edit_anchored_panel`` posture).
    ``expire=True`` tears the session down after the edit (terminal
    edits — the shipped ``view.stop()``)."""
    if _message_editor is None:
        return EDIT_UNAVAILABLE
    session = _sessions.get(message_key)
    if session is None or session.expired:
        return EDIT_MISSING
    if session.channel_id is None:
        return EDIT_MISSING          # no editable channel message exists
    try:
        message_id = int(str(session.message_ref
                             if session.message_ref is not None
                             else message_key))
    except (TypeError, ValueError):
        return EDIT_MISSING          # opaque non-message handle
    spec = get_panel(session.panel_id)
    ctx = PanelContext(
        bot=None, guild_id=guild_id, actor=actor,
        channel_id=session.channel_id, origin=PanelOrigin.ANCHOR,
        audience=spec.audience, locale=LocaleContext(),
        params=dict(params or {}), surface=None)
    rendered = await _render_session_panel(spec, session, ctx)
    outcome = await _message_editor(rendered,
                                    channel_id=int(session.channel_id),
                                    message_id=message_id)
    if expire:
        _expire_session(message_key, session)
    return outcome


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
    elif binding.kind == "browse":
        await _handle_browse(binding.target, req)
    elif binding.kind == "selwin":
        await _handle_selwin(binding.target, req)
    else:  # pragma: no cover — the registry mints only the recognized kinds
        raise ValueError(f"unknown nav binding kind {binding.kind!r}")


async def _handle_browse(custom_id: str, req: ResolveRequest) -> None:
    """Dispatch a BrowserView control click (D-0034): decode the current
    state against the panel spec, apply the click's delta (a sort/filter
    select carries its new value in ``req.args['values']``; a prev/next button
    steps the page), and re-render the panel with the new browse state — data
    re-resolved fresh at click time (§2.4). A malformed/stale id (unknown
    panel, or a block that is no longer browsable) decodes to None and
    degrades to the §3.4 polite-expiry terminal — never a crash, never a
    mis-render."""
    from sb.kernel.panels import browserview
    from sb.kernel.panels.router import EXPIRY_MESSAGE

    async def _expire() -> None:
        try:
            await req.responder.deny(EXPIRY_MESSAGE, ephemeral=True)
        except Exception:  # noqa: BLE001 — a failed expiry render never raises
            logger.warning("browse expiry render failed for %r", custom_id,
                           exc_info=True)

    panel_id = browserview.panel_id_of(custom_id)
    if panel_id is None:
        await _expire()
        return
    try:
        spec = get_panel(panel_id)
    except LookupError:
        await _expire()
        return
    decoded = browserview.decode(custom_id, spec)
    if decoded is None:
        await _expire()
        return
    control, block, state = decoded
    block_spec = browserview.browse_block_spec(spec, block)
    values = req.args.get("values") if req.args else None
    new_state = browserview.apply_delta(control, state, block_spec, values)
    await _render_and_present(spec, req, browse=new_state)


async def _handle_selwin(custom_id: str, req: ResolveRequest) -> None:
    """Dispatch a windowed-select ◀ Prev / Next ▶ click (the windowed-select
    grammar successor): decode the current window against the panel spec,
    step it, and re-render with the new window — the options re-resolve
    fresh at click time (§2.4), and the upper bound clamps at render where
    the fresh count is known. A live session under the clicked message
    refreshes IN PLACE (the shipped SelectWindow edited its own message; a
    window flip must never spawn a second card); without one it re-presents
    (the browse/page-turn posture). A malformed/stale id — unknown panel,
    unknown selector, or a selector no longer declared windowed — degrades
    to the §3.4 polite-expiry terminal, never a crash."""
    from sb.kernel.panels import selectwindow
    from sb.kernel.panels.router import EXPIRY_MESSAGE

    async def _expire() -> None:
        try:
            await req.responder.deny(EXPIRY_MESSAGE, ephemeral=True)
        except Exception:  # noqa: BLE001 — a failed expiry render never raises
            logger.warning("selwin expiry render failed for %r", custom_id,
                           exc_info=True)

    panel_id = selectwindow.window_panel_id(custom_id)
    if panel_id is None:
        await _expire()
        return
    try:
        spec = get_panel(panel_id)
    except LookupError:
        await _expire()
        return
    decoded = selectwindow.decode_window(custom_id, spec)
    if decoded is None:
        await _expire()
        return
    control, _selector, state = decoded
    new_state = selectwindow.apply_window_delta(control, state)
    message = getattr(req.origin, "message", None)
    message_key = str(getattr(message, "id", "") or "")
    if message_key:
        try:
            refreshed = await refresh_session_view(
                req, message_key=message_key,
                params={selectwindow.WINDOW_PARAM: new_state})
            if refreshed:
                return
        except Exception:  # noqa: BLE001 — degrade to the fresh present
            logger.warning("selwin in-place refresh failed for %r", custom_id,
                           exc_info=True)
    await _render_and_present(spec, req, window=new_state)

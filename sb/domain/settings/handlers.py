"""Settings-surface handlers — the ``!settings access`` front door plus
the declared + honest pending terminals for every hub click whose target
is its own port slice (the role/utility/channel-band precedent, never a
silent stub): the per-group settings pages (``settings_subsystem.*``),
the audit view and the Command Access panel
(``settings_command_access.*``, PR-6) stay pending with their own
slices. The Access Policy Explorer's six controls are ARMED (curation
rows 82-87) over the governance diagnostic read seam
(``governance.resolve_subsystem_state``) and the K7 ``SET_VISIBILITY``
clear lane (Reset); the hub's three READ-ONLY diagnostics (Needs setup /
Invalid settings / Missing bindings — settings-admin slice 1) are ARMED
as declared PanelRef open-child routes (sb/domain/settings/panels.py) —
no handler here, the grammar owns the dispatch. Refs register at MODULE
IMPORT (the composition-parity invariant — the live root never runs
ENSURE_REFS)."""

from __future__ import annotations

import dataclasses
import logging

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request

logger = logging.getLogger("sb.domain.settings")

__all__ = ["Reply", "ensure_handler_refs"]

_PENDING = " ports with the settings-mutation panel slice."

#: settings groups whose page is a REAL dedicated panel that is NOT the
#: operator-spine ``<group>.hub`` shape — ``games.hub`` is the PLAYER games
#: hub (band 6 parity flip), so the D-0082 §5 sections settings surface
#: lives at its own id and the group select routes here first.
_GROUP_PANELS: dict[str, str] = {
    "games": "games.sections",
}

# --- the explorer's per-message session state ---------------------------------
#
# The engine's ephemeral bindings freeze the OPENING args, so the running
# selection (subsystem / scope / roster page) lives here, keyed by the
# panel message id (the ``refresh_session_view`` message key — the games
# sections ``_refresh_page`` precedent). In-memory like the engine's own
# session table: a restart falls back to the polite text degrade.
_ACCESS_SESSIONS: dict[str, dict] = {}
_ACCESS_SESSIONS_MAX = 512

_ACCESS_EXPIRED = ("🔍 This explorer session has expired — reopen it with "
                   "`!settings access`.")
_ACCESS_PICK_FIRST = ("🔍 Pick a subsystem from the first dropdown first "
                      "(and a scope — Channel is the default).")


def _display_name(req) -> str:
    """The invoking member's display name (the shipped ``ctx.author``
    read — the economy author-display / rps precedent)."""
    user = getattr(req.origin, "author", None) or getattr(req.origin, "user", None)
    name = (getattr(user, "display_name", None)
            or getattr(user, "name", None))
    return str(name) if name else "unknown"


def _message_key(req) -> str:
    message = getattr(req.origin, "message", None)
    return str(getattr(message, "id", "") or "")


def _access_state(req) -> tuple[str, dict] | tuple[None, None]:
    """The explorer's selection state for the clicked panel message —
    (None, None) when the click carries no message handle."""
    key = _message_key(req)
    if not key:
        return None, None
    state = _ACCESS_SESSIONS.setdefault(
        key, {"subsystem": "", "scope": "channel", "page": 1})
    while len(_ACCESS_SESSIONS) > _ACCESS_SESSIONS_MAX:
        _ACCESS_SESSIONS.pop(next(iter(_ACCESS_SESSIONS)))
    return key, state


def _category_id(req) -> int | None:
    """The invoked-in channel's category id, when the origin carries it
    (interaction.channel.category_id); None = no category axis."""
    channel = getattr(req.origin, "channel", None)
    raw = getattr(channel, "category_id", None)
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _refresh_params(req, state: dict) -> dict:
    """The re-render params (the renderer override + fields provider read
    these): the running selection + the click-time scope context. The
    clicker IS the invoker (invoker-locked panel), so the author-lock
    footer name re-derives from the click."""
    return {
        "invoker_name": _display_name(req),
        "access_subsystem": state["subsystem"],
        "access_scope": state["scope"],
        "access_page": state["page"],
        "category_id": _category_id(req),
    }


async def _refresh_access(req, key: str, state: dict) -> bool:
    """Best-effort in-place re-render (the games-sections ``_refresh_page``
    posture: a miss degrades to the caller's text reply, never an error)."""
    try:
        from sb.kernel.panels.engine import refresh_session_view

        return await refresh_session_view(
            req, message_key=key, params=_refresh_params(req, state))
    except Exception:  # noqa: BLE001 — the caller degrades to text
        logger.debug("settings.access refresh failed", exc_info=True)
        return False


async def _resolve_selection(req, state: dict):
    """The governance diagnostic read for the current selection (lazy
    domain→governance import — the sections.py seam shape, PL-001)."""
    from sb.domain.governance import service as governance
    from sb.domain.settings.panels import _access_axes

    params = {"category_id": _category_id(req)}
    return await governance.resolve_subsystem_state(
        int(req.guild_id or 0), state["subsystem"],
        **_access_axes(params, state["scope"], req.channel_id))


def _summary_text(res, state: dict) -> str:
    """The one-line degrade summary (refresh miss / restart)."""
    from sb.domain.settings.panels import (
        _ACCESS_SCOPE_LABELS,
        _ACCESS_STATE_BADGES,
    )

    badge = _ACCESS_STATE_BADGES.get(res.state.value, res.state.value)
    if not res.known:
        provenance = "unregistered subsystem — fail-open"
    elif res.source.value == "registry_default":
        provenance = "registry default (no override)"
    elif res.source.value == "dependency_block":
        provenance = "dependency block: " + ", ".join(res.dependency_blocks)
    else:
        provenance = f"{res.source.value} override"
    scope_label = _ACCESS_SCOPE_LABELS.get(state["scope"], state["scope"])
    return (f"🔍 `{res.subsystem}` @ {scope_label}: {badge} — {provenance}")


def _explain_text(res, state: dict) -> str:
    """The Explain Access decision chain — the walked scopes in resolver
    order, the matched row, the registry-default terminus and any
    dependency block, verbatim from the read seam."""
    from sb.domain.settings.panels import (
        _ACCESS_SCOPE_LABELS,
        _ACCESS_STATE_BADGES,
    )

    scope_label = _ACCESS_SCOPE_LABELS.get(state["scope"], state["scope"])
    lines = [f"🔬 **Access resolution — `{res.subsystem}` "
             f"({scope_label})**"]
    if not res.known:
        lines.append(
            "Unregistered subsystem — the compiled manifests own existence; "
            "governance gates only registered rows, so access is fail-open "
            "**enabled** (the dispatch-gate semantics).")
        return "\n".join(lines)
    step = 0
    for check in res.checks:
        step += 1
        where = f"{check.scope_type} `{check.scope_id}`"
        if check.matched:
            verdict = "enabled" if check.value else "disabled"
            lines.append(f"{step}. {where} — **override: {verdict}** "
                         "← matched")
        elif check.has_row and check.value is None:
            lines.append(f"{step}. {where} — explicit inherit "
                         "(falls through)")
        elif check.has_row:
            verdict = "enabled" if check.value else "disabled"
            lines.append(f"{step}. {where} — override: {verdict} "
                         "(shadowed by a more specific scope)")
        else:
            lines.append(f"{step}. {where} — no override row")
    lines.append(f"{step + 1}. registry default — enabled "
                 f"(visibility tier: {res.visibility_tier})")
    if res.dependency_blocks:
        lines.append("Dependency block: "
                     + ", ".join(f"`{d}`" for d in res.dependency_blocks)
                     + " disabled — hard dependencies propagate.")
    badge = _ACCESS_STATE_BADGES.get(res.state.value, res.state.value)
    lines.append(f"→ {badge}")
    return "\n".join(lines)


def _register() -> None:
    from sb.domain.operator_spine import pending_handler
    from sb.spec.refs import HandlerRef, handler, is_registered

    # The three read-only diagnostics' pending refs are RETIRED
    # (settings-admin slice 1 armed them as PanelRef open-child routes —
    # the retired-explorer-pending precedent); audit + command access
    # keep their honest terminals until their own slices land.
    pending_handler("settings.group_pending",
                    f"⚙️ The per-group settings page{_PENDING}")
    pending_handler("settings.audit_pending",
                    f"🕒 The Recent-changes audit view{_PENDING}")
    pending_handler("settings.command_access_pending",
                    f"🚪 The Command Access panel{_PENDING}")

    if is_registered(HandlerRef("settings.access_view")):
        return

    @handler("settings.open_group")
    async def open_group(req):
        """The Settings-hub "Open a settings group…" select — the shipped
        ``SettingsHubView`` group select NAVIGATED (read-only, never a
        mutation) to each group's page. Restore that navigation as a
        faithful READ SUBSET: open the group's read-only operator-spine hub
        when one is ensured (welcome/counters/security/automod/
        image_moderation) or the group's dedicated settings panel
        (``_GROUP_PANELS`` — the D-0082 games sections surface); every
        other group keeps the honest pending terminal until the
        settings-mutation panel slice ports the full edit page. This
        handler only NAVIGATES — open_panel or BLOCKED, never a write
        seam (mirrors ``help.open_category``); the games sections panel's
        own components carry the mutations."""
        from sb.domain.operator_spine import has_operator_hub
        from sb.kernel.panels.engine import open_panel
        from sb.spec.outcomes import BLOCKED
        from sb.spec.refs import PanelRef

        values = tuple(req.args.get("values", ()) or ())
        group = str(values[0]) if values else ""
        if group in _GROUP_PANELS:
            await open_panel(PanelRef(_GROUP_PANELS[group]), req)
            return None
        if group and has_operator_hub(group):
            await open_panel(PanelRef(f"{group}.hub"), req)
            return None
        # the per-group scalar edit + reset is the settings-mutation slice's
        # port (write-seam-gated) — read-only nav lands here until then.
        return Reply(BLOCKED, f"⚙️ The per-group settings page{_PENDING}")

    @handler("settings.access_view")
    async def access_view(req):
        """``!settings access`` — open the shipped Access Policy Explorer
        (goldens/settings/sweep_settings_access). The invoker's display
        name rides the request args so the renderer override can stamp
        the shipped author-lock footer (the economy author-display
        precedent)."""
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(
            PanelRef("settings.access"),
            dataclasses.replace(req, args={**dict(req.args),
                                           "invoker_name": _display_name(req)}))
        return None

    # --- the armed explorer controls (curation rows 82-87) ------------------
    # All READS through governance.resolve_subsystem_state except Reset
    # (the ONE write — the K7 SET_VISIBILITY clear lane, enabled=None =
    # override delete; the games-sections precedent). A successful in-place
    # refresh returns None (the edit IS the ack — the open_group posture);
    # a refresh miss degrades to an honest text reply.

    from sb.spec.outcomes import SUCCESS

    @handler("settings.access_subsystem")
    async def access_subsystem(req):
        """Pick a subsystem → the explorer re-renders its resolved state."""
        values = tuple(req.args.get("values", ()) or ())
        subsystem = str(values[0]) if values else ""
        key, state = _access_state(req)
        if not subsystem or state is None:
            return Reply(SUCCESS, _ACCESS_EXPIRED)
        state["subsystem"] = subsystem
        if await _refresh_access(req, key, state):
            return None
        return Reply(SUCCESS,
                     _summary_text(await _resolve_selection(req, state),
                                   state))

    @handler("settings.access_scope")
    async def access_scope(req):
        """Pick a scope → re-resolve the selection at that scope."""
        values = tuple(req.args.get("values", ()) or ())
        scope = str(values[0]) if values else ""
        key, state = _access_state(req)
        if scope not in ("channel", "category", "guild") or state is None:
            return Reply(SUCCESS, _ACCESS_EXPIRED)
        state["scope"] = scope
        if await _refresh_access(req, key, state):
            return None
        if not state["subsystem"]:
            return Reply(SUCCESS, _ACCESS_PICK_FIRST)
        return Reply(SUCCESS,
                     _summary_text(await _resolve_selection(req, state),
                                   state))

    @handler("settings.access_explain")
    async def access_explain(req):
        """🔬 Explain Access — render the resolution chain for the
        selection (a pure read; the reply IS the diagnostic)."""
        _, state = _access_state(req)
        if state is None:
            return Reply(SUCCESS, _ACCESS_EXPIRED)
        if not state["subsystem"]:
            return Reply(SUCCESS, _ACCESS_PICK_FIRST)
        res = await _resolve_selection(req, state)
        return Reply(SUCCESS, _explain_text(res, state))

    @handler("settings.access_reset")
    async def access_reset(req):
        """🔄 Reset — clear the selection's override row at the selected
        scope (the K7 ``SET_VISIBILITY`` lane with ``enabled=None`` = the
        override DELETE; audited, actor-authorized — the games-sections
        Enable-all precedent). Access then re-resolves from the next
        scope up."""
        from sb.domain.governance import service as governance

        key, state = _access_state(req)
        if state is None:
            return Reply(SUCCESS, _ACCESS_EXPIRED)
        if not state["subsystem"]:
            return Reply(SUCCESS, _ACCESS_PICK_FIRST)
        if not req.guild_id:
            return Reply(SUCCESS, "❌ Access policy is per server — use "
                                  "this in a guild.")
        scope = state["scope"]
        if scope == "guild":
            scope_id = int(req.guild_id)
        elif scope == "category":
            category = _category_id(req)
            if category is None:
                return Reply(SUCCESS, "❌ This channel has no category — "
                                      "pick another scope to reset.")
            scope_id = category
        else:
            scope_id = int(req.channel_id or 0)
        result = await governance.set_subsystem_visibility(
            ctx_from_request(req, {}), scope_type=scope, scope_id=scope_id,
            subsystem=state["subsystem"], enabled=None)
        if getattr(result, "outcome", None) != SUCCESS:
            return Reply(
                getattr(result, "outcome", "error"),
                f"❌ Couldn't reset `{state['subsystem']}` at {scope} "
                f"scope: "
                f"{getattr(result, 'user_message', '') or 'write failed'}")
        await _refresh_access(req, key, state)
        return Reply(SUCCESS,
                     f"✅ Cleared the {scope} override for "
                     f"`{state['subsystem']}` — access re-resolves from "
                     "the next scope up.")

    @handler("settings.access_page")
    async def access_page(req):
        """◀ Prev / Next ▶ — page the subsystem roster (page 1 = the
        golden-pinned 25; page 2 = the registry remainder). Stale clicks
        clamp to the page bounds (the buttons render disabled at the
        edges, but a raced click may still arrive)."""
        from sb.domain.settings.panels import access_page_count

        key, state = _access_state(req)
        if state is None:
            return Reply(SUCCESS, _ACCESS_EXPIRED)
        action = str(req.args.get("session_action") or "")
        step = 1 if action == "access_next" else -1
        state["page"] = min(max(state["page"] + step, 1),
                            access_page_count())
        if await _refresh_access(req, key, state):
            return None
        return Reply(SUCCESS, _ACCESS_EXPIRED)


_register()


def ensure_handler_refs() -> None:
    _register()

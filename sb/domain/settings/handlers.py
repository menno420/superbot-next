"""Settings-surface handlers — the ``!settings access`` front door plus
the settings-hub sub-surface controls. Every pending terminal is now
RETIRED: the Access Policy Explorer's six controls are ARMED (curation
rows 82-87) over the governance diagnostic read seam
(``governance.resolve_subsystem_state``) and the K7 ``SET_VISIBILITY``
clear lane (Reset); the hub's three READ-ONLY diagnostics (Needs setup /
Invalid settings / Missing bindings — settings-admin slice 1) and the
🕒 Recent-changes audit view (slice 2) are ARMED as declared PanelRef
open-child routes (sb/domain/settings/panels.py) — no handler here, the
grammar owns the dispatch. The 🚪 Command Access panel is ARMED the same
way (settings-admin slice 3) with its WRITE controls handled below over
the live platform command-access K7 lanes (``platform.set_access_mode``
/ ``set_access_channels`` — the setup-wizard step-8 seam, reused, never
re-minted). Settings epic S0 ports the per-group scalar EDIT page:
``settings.open_group``'s non-hub arm now opens ``settings.group_edit``
(owner ruling option A) — the last ``settings.group_pending`` terminal
is retired, and the edit/reset controls below ride the K7
``settings.set_scalar`` / ``clear_scalar`` scalar lanes (the S1 bool
toggle wired end to end; S2–S7 add the per-type widgets). Refs register
at MODULE IMPORT (the composition-parity invariant — the live root never
runs ENSURE_REFS)."""

from __future__ import annotations

import dataclasses
import logging

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request

logger = logging.getLogger("sb.domain.settings")

__all__ = ["Reply", "ensure_handler_refs"]

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

#: the Command-Access mode buttons → the shipped K7 mode values (the
#: session_action arg carries the clicked action_id — the access_page
#: discrimination precedent).
_CA_MODES: dict[str, str] = {
    "ca_all_channels": "all_channels",
    "ca_selected_channels": "selected_channels",
    "ca_disabled": "disabled_except_bootstrap",
}

#: the shipped no-guild guard copy (edit_command_access.py), verbatim.
_CA_GUILD_ONLY = ("❌ Command access can only be configured inside a "
                  "server.")


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


async def _refresh_command_access(req) -> bool:
    """Best-effort in-place re-render of the Command-Access panel after a
    successful write (the oracle's ``_refresh_panel`` edit — the
    ``_refresh_access`` posture: a miss degrades to the caller's text
    confirmation, never an error). No params: the fields provider reads
    the live policy snapshot (the write lanes forget the cache
    post-commit)."""
    key = _message_key(req)
    if not key:
        return False
    try:
        from sb.kernel.panels.engine import refresh_session_view

        return await refresh_session_view(req, message_key=key, params={})
    except Exception:  # noqa: BLE001 — the caller's text reply answers
        logger.debug("settings.command_access refresh failed", exc_info=True)
        return False


# --- the ported per-group EDIT page write path (settings epic S0) ---------------
#
# The oracle SubsystemSettingsView's edit/reset selects dispatched by
# SettingSpec type onto the shipped SettingsMutationPipeline; here they ride
# the LIVE K7 scalar lanes (settings.set_scalar / clear_scalar — sb/domain/
# settings/ops.py, the ADMIN-floor write path, no new op minted). S0 wires
# the S1 BOOL toggle end to end; the per-type widgets (S2–S7) land later, so
# a non-bool pick degrades to an honest terminal rather than a dead control.
# The selected group rides the click's args (GROUP_EDIT_PARAM — baked onto
# every session-minted child at open), never a parallel session dict.

_GROUP_EDIT_EXPIRED = ("⚙️ This settings session expired — reopen the group "
                       "from `!settings`.")


async def _run_scalar_op(req, op, params: dict):
    """Run a K7 scalar CompoundOp (set_scalar / clear_scalar) on the click's
    actor/guild — the command_access.set_access_mode invocation shape
    (``engine.run(op, ctx_from_request(req, params))``)."""
    from sb.kernel.workflow import engine as _engine

    return await _engine.run(op, ctx_from_request(req, params))


async def _refresh_group_edit(req, group: str) -> bool:
    """Best-effort in-place re-render of the group_edit page after a write
    (the _refresh_command_access posture): re-supply the running group so
    the read embed shows the new effective value; a miss degrades to the
    caller's text confirmation."""
    key = _message_key(req)
    if not key:
        return False
    try:
        from sb.domain.settings.panels import GROUP_EDIT_PARAM
        from sb.kernel.panels.engine import refresh_session_view

        return await refresh_session_view(
            req, message_key=key, params={GROUP_EDIT_PARAM: group})
    except Exception:  # noqa: BLE001 — the caller's text reply answers
        logger.debug("settings.group_edit refresh failed", exc_info=True)
        return False


async def _refresh_group_edit_enum(req, group: str, name: str) -> bool:
    """Best-effort in-place re-render of the enum picker after a write
    (the _refresh_group_edit posture, one axis further): re-supply BOTH the
    group and the setting so the picker's options re-mark the new current
    value; a miss degrades to the caller's text confirmation."""
    key = _message_key(req)
    if not key:
        return False
    try:
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )
        from sb.kernel.panels.engine import refresh_session_view

        return await refresh_session_view(
            req, message_key=key,
            params={GROUP_EDIT_PARAM: group, GROUP_EDIT_SETTING_PARAM: name})
    except Exception:  # noqa: BLE001 — the caller's text reply answers
        logger.debug("settings.group_edit_enum refresh failed", exc_info=True)
        return False


async def _refresh_group_edit_number(req, group: str, name: str) -> bool:
    """Best-effort in-place re-render of the number widget after a write
    (the _refresh_group_edit_enum posture): re-supply BOTH the group and the
    setting so the prompt re-reads the new effective value; a miss degrades to
    the caller's text confirmation."""
    key = _message_key(req)
    if not key:
        return False
    try:
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )
        from sb.kernel.panels.engine import refresh_session_view

        return await refresh_session_view(
            req, message_key=key,
            params={GROUP_EDIT_PARAM: group, GROUP_EDIT_SETTING_PARAM: name})
    except Exception:  # noqa: BLE001 — the caller's text reply answers
        logger.debug("settings.group_edit_number refresh failed", exc_info=True)
        return False


async def _refresh_group_edit_text(req, group: str, name: str) -> bool:
    """Best-effort in-place re-render of the text widget after a write (the
    _refresh_group_edit_number twin): re-supply BOTH the group and the setting
    so the prompt re-reads the new effective value; a miss degrades to the
    caller's text confirmation."""
    key = _message_key(req)
    if not key:
        return False
    try:
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )
        from sb.kernel.panels.engine import refresh_session_view

        return await refresh_session_view(
            req, message_key=key,
            params={GROUP_EDIT_PARAM: group, GROUP_EDIT_SETTING_PARAM: name})
    except Exception:  # noqa: BLE001 — the caller's text reply answers
        logger.debug("settings.group_edit_text refresh failed", exc_info=True)
        return False


async def _refresh_group_edit_channel(req, group: str, name: str) -> bool:
    """Best-effort in-place re-render of the channel picker after a write (the
    _refresh_group_edit_enum twin): re-supply BOTH the group and the setting so
    the picker's options re-mark the new current channel; a miss degrades to
    the caller's text confirmation."""
    key = _message_key(req)
    if not key:
        return False
    try:
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )
        from sb.kernel.panels.engine import refresh_session_view

        return await refresh_session_view(
            req, message_key=key,
            params={GROUP_EDIT_PARAM: group, GROUP_EDIT_SETTING_PARAM: name})
    except Exception:  # noqa: BLE001 — the caller's text reply answers
        logger.debug("settings.group_edit_channel refresh failed",
                     exc_info=True)
        return False


async def _refresh_group_edit_presets(req, group: str, name: str) -> bool:
    """Best-effort in-place re-render of the presets widget after a write (the
    _refresh_group_edit_channel twin): re-supply BOTH the group and the setting
    so the quick-set buttons re-mark the new current value; a miss degrades to
    the caller's text confirmation."""
    key = _message_key(req)
    if not key:
        return False
    try:
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )
        from sb.kernel.panels.engine import refresh_session_view

        return await refresh_session_view(
            req, message_key=key,
            params={GROUP_EDIT_PARAM: group, GROUP_EDIT_SETTING_PARAM: name})
    except Exception:  # noqa: BLE001 — the caller's text reply answers
        logger.debug("settings.group_edit_presets refresh failed",
                     exc_info=True)
        return False


def _group_edit_selection(req):
    """(group, setting_name) from a group_edit select click: the group rides
    the minted-child args (GROUP_EDIT_PARAM), the picked setting rides the
    ordinary select ``values`` round-trip."""
    from sb.domain.settings.panels import GROUP_EDIT_PARAM

    group = str(req.args.get(GROUP_EDIT_PARAM) or "")
    values = tuple(req.args.get("values", ()) or ())
    name = str(values[0]) if values else ""
    return group, name


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
    from sb.spec.refs import HandlerRef, handler, is_registered

    # Every settings-hub sub-surface's pending terminal is now RETIRED:
    # slices 1-3 armed the read-only diagnostics / audit view / Command
    # Access door as real routes, and settings epic S0 retired the LAST
    # one — ``settings.group_pending`` — by porting the per-group scalar
    # EDIT page (``settings.group_edit``); open_group now routes non-hub
    # groups there (option A). Nothing pending remains in this subsystem.

    if is_registered(HandlerRef("settings.access_view")):
        return

    @handler("settings.open_group")
    async def open_group(req):
        """The Settings-hub "Open a settings group…" select — the shipped
        ``SettingsHubView`` group select NAVIGATED (read-only, never a
        mutation) to each group's page. The port's three-way branch (owner
        ruling option A, docs/question-router.md → Answered):

          1. the group's dedicated settings panel (``_GROUP_PANELS`` — the
             D-0082 games sections surface) — UNTOUCHED by S0;
          2. the group's read-only operator-spine hub when one is ensured
             (welcome/counters/security/automod/image_moderation) —
             UNTOUCHED by S0;
          3. every OTHER (non-hub) group opens the ported per-group scalar
             EDIT page ``settings.group_edit`` (settings epic S0) — this is
             the arm option A re-points, displacing the retired
             ``settings.group_pending`` terminal.

        This handler only NAVIGATES — open_panel, never a write seam
        (mirrors ``help.open_category``); the group_edit page's own
        components carry the S1+ mutations. The selected group rides the
        opening request's args so the engine bakes it onto every minted
        child (the session-view group axis; see panels.py GROUP_EDIT_PARAM)."""
        import dataclasses as _dc

        from sb.domain.operator_spine import has_operator_hub
        from sb.domain.settings.panels import GROUP_EDIT_PARAM
        from sb.kernel.panels.engine import open_panel
        from sb.spec.outcomes import BLOCKED
        from sb.spec.refs import PanelRef

        values = tuple(req.args.get("values", ()) or ())
        group = str(values[0]) if values else ""
        if not group:
            return Reply(BLOCKED,
                         "⚙️ Pick a settings group from the dropdown.")
        if group in _GROUP_PANELS:
            await open_panel(PanelRef(_GROUP_PANELS[group]), req)
            return None
        if has_operator_hub(group):
            await open_panel(PanelRef(f"{group}.hub"), req)
            return None
        # option A: the non-hub arm opens the ported per-group scalar edit
        # page. The group rides the opening args (GROUP_EDIT_PARAM) so the
        # engine's session-mint bakes it onto every child — the running
        # selection needs no parallel session dict.
        await open_panel(
            PanelRef("settings.group_edit"),
            _dc.replace(req, args={**dict(req.args),
                                   GROUP_EDIT_PARAM: group}))
        return None

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

    # --- the armed Command Access panel controls (settings-admin slice 3) ---
    # The set's ONE write surface (oracle disbot/views/settings/
    # edit_command_access.py). Every mutation rides the LIVE platform
    # command-access K7 lanes — platform.set_access_mode /
    # set_access_channels (sb/domain/platform/command_access.py, the
    # setup-wizard step-8 seam): audited compound ops, administrator
    # authority floor (the engine's K6 check — the oracle's per-callback
    # admin guard, structural here; the panel controls also carry
    # audience_tier="administrator"), post-commit cache forget. A
    # successful write refreshes the panel in place (the fields provider
    # re-reads the live snapshot) then confirms with the shipped copy —
    # the oracle's edit + ephemeral-followup pair (the access_reset
    # posture). No session state: the DB snapshot IS the panel state.

    @handler("settings.ca_mode")
    async def ca_mode(req):
        """One shipped mode button (🌐 All / 📋 Selected / 🚫 Disabled) —
        the session_action discriminates (the access_page precedent);
        writes through platform.set_access_mode."""
        from sb.domain.platform import command_access
        from sb.spec.outcomes import BLOCKED

        if not req.guild_id:
            # shipped guard copy, verbatim.
            return Reply(BLOCKED, _CA_GUILD_ONLY)
        mode = _CA_MODES.get(str(req.args.get("session_action") or ""))
        if mode is None:
            return Reply(BLOCKED, "❌ Unknown command access mode.")
        result = await command_access.set_access_mode(
            ctx_from_request(req, {}), mode=mode)
        if getattr(result, "outcome", None) != SUCCESS:
            return Reply(
                getattr(result, "outcome", "error"),
                f"❌ Couldn't set the command access mode: "
                f"{getattr(result, 'user_message', '') or 'write failed'}")
        await _refresh_command_access(req)
        from sb.domain.settings.panels import _CA_MODE_LABELS

        # shipped confirmation copy, verbatim.
        return Reply(SUCCESS, f"✅ Command access mode set to "
                              f"**{_CA_MODE_LABELS[mode]}**.")

    @handler("settings.ca_channels")
    async def ca_channels(req):
        """The shipped multi-ChannelSelect — the atomic allowlist replace
        (platform.set_access_channels: full DELETE + re-INSERT in one
        leg; the oracle replace_allowed_channels shape). A blank
        selection CLEARS the list (allow_empty — the shipped
        min_values=0 contract)."""
        from sb.domain.platform import command_access
        from sb.spec.outcomes import BLOCKED

        if not req.guild_id:
            # shipped guard copy, verbatim.
            return Reply(BLOCKED, _CA_GUILD_ONLY)
        channel_ids = tuple(
            int(v) for v in (req.args.get("values", ()) or ())
            if str(v).isdigit())
        result = await command_access.set_access_channels(
            ctx_from_request(req, {}), channel_ids=channel_ids,
            allow_empty=True)
        if getattr(result, "outcome", None) != SUCCESS:
            return Reply(
                getattr(result, "outcome", "error"),
                f"❌ Couldn't update the allowed channels: "
                f"{getattr(result, 'user_message', '') or 'write failed'}")
        await _refresh_command_access(req)
        # shipped confirmation copy, verbatim (both branches).
        if channel_ids:
            return Reply(
                SUCCESS,
                f"✅ Allowed channels updated ({len(channel_ids)} "
                f"channel{'s' if len(channel_ids) != 1 else ''}).")
        return Reply(SUCCESS, "✅ Allowed channel list cleared.")

    # --- the ported per-group EDIT page controls (settings epic S0) ---------
    # The oracle SubsystemSettingsView edit/reset selects + Open-Panel
    # button. The Edit select dispatches by SettingSpec type: S0 wires the
    # S1 BOOL toggle (flip → settings.set_scalar); the per-type widgets
    # (enum / number / text / channel / role / presets) land as S2–S7, so a
    # non-bool pick degrades to an honest terminal. The Reset select clears
    # through settings.clear_scalar. Every write rides the ADMIN-floor K7
    # scalar lanes — no new op minted.

    @handler("settings.group_edit_pick")
    async def group_edit_pick(req):
        """The windowed "Edit a setting…" select — dispatch by the picked
        SettingSpec's value type. S1: bool toggles in place through
        settings.set_scalar (the flipped effective value). S2: an enum-shaped
        scalar (str + allowed_values) opens the windowed enum picker
        (settings.group_edit_enum). The remaining per-type widgets land in a
        later slice (S3–S7)."""
        from sb.domain.settings.ops import SET_SCALAR
        from sb.domain.settings.panels import (
            _group_edit_spec,
            _is_channel_spec,
            _is_enum_spec,
            _is_number_spec,
            _is_presets_spec,
            _is_text_spec,
        )
        from sb.spec.outcomes import BLOCKED

        group, name = _group_edit_selection(req)
        if not group or not name:
            return Reply(SUCCESS, _GROUP_EDIT_EXPIRED)
        spec = _group_edit_spec(group, name)
        if spec is None:
            return Reply(BLOCKED, f"⚙️ Unknown setting `{group}.{name}`.")
        # S1 — bool toggle: flip the effective value in place.
        if spec.is_bool:
            if not req.guild_id:
                return Reply(BLOCKED, "❌ Settings are per server — use this "
                                      "inside a server.")
            from sb.kernel import settings as ksettings

            current = bool(await ksettings.resolve(
                int(req.guild_id), group, name))
            new_value = "false" if current else "true"
            key = ksettings.persisted_key(group, name)
            result = await _run_scalar_op(req, SET_SCALAR,
                                          {"key": key, "value": new_value})
            if getattr(result, "outcome", None) != SUCCESS:
                return Reply(
                    getattr(result, "outcome", "error"),
                    f"❌ Couldn't update `{group}.{name}`: "
                    f"{getattr(result, 'user_message', '') or 'write failed'}")
            await _refresh_group_edit(req, group)
            return Reply(SUCCESS,
                         f"✅ `{group}.{name}` set to **{not current}**.")
        # S5 — channel select: a `channel`-hinted scalar opens the windowed
        # channel picker (the oracle ChannelSettingSelectView). The oracle
        # checks input_hint FIRST, so this arm is routed BEFORE the enum /
        # number / text value_type arms — otherwise a channel-hinted `int`
        # would misroute to the S3 number modal. The group + picked setting
        # ride the opening args so the child session-view bakes them onto the
        # session-minted select; a channel click commits through set_scalar.
        if _is_channel_spec(spec):
            import dataclasses as _dc

            from sb.domain.settings.panels import (
                GROUP_EDIT_PARAM,
                GROUP_EDIT_SETTING_PARAM,
            )
            from sb.kernel.panels.engine import open_panel
            from sb.spec.refs import PanelRef

            await open_panel(
                PanelRef("settings.group_edit_channel"),
                _dc.replace(req, args={**dict(req.args),
                                       GROUP_EDIT_PARAM: group,
                                       GROUP_EDIT_SETTING_PARAM: name}))
            return None
        # S7 — numeric-presets quick-set: a `numeric_presets`-hinted scalar (a
        # declared `presets` tuple) opens the quick-set buttons widget (the
        # oracle NumericPresetsView). The oracle checks input_hint FIRST, so this
        # arm — like the S5 channel arm — is routed BEFORE the enum / number /
        # text value_type arms: a presets-hinted `int` satisfies _is_number_spec
        # too, so ordering (not the predicate) is what keeps it off the S3 number
        # modal. The group + picked setting ride the opening args so the child
        # session-view bakes them onto the session-minted buttons; a preset click
        # commits its fixed value through set_scalar.
        if _is_presets_spec(spec):
            import dataclasses as _dc

            from sb.domain.settings.panels import (
                GROUP_EDIT_PARAM,
                GROUP_EDIT_SETTING_PARAM,
            )
            from sb.kernel.panels.engine import open_panel
            from sb.spec.refs import PanelRef

            await open_panel(
                PanelRef("settings.group_edit_presets"),
                _dc.replace(req, args={**dict(req.args),
                                       GROUP_EDIT_PARAM: group,
                                       GROUP_EDIT_SETTING_PARAM: name}))
            return None
        # S2 — enum select: open the windowed picker of the declared
        # allowed_values (the oracle build_enum_select_view). The group + the
        # picked setting ride the opening args so the engine bakes them onto
        # the session-minted select; a value click commits through set_scalar.
        if _is_enum_spec(spec):
            import dataclasses as _dc

            from sb.domain.settings.panels import (
                GROUP_EDIT_PARAM,
                GROUP_EDIT_SETTING_PARAM,
            )
            from sb.kernel.panels.engine import open_panel
            from sb.spec.refs import PanelRef

            await open_panel(
                PanelRef("settings.group_edit_enum"),
                _dc.replace(req, args={**dict(req.args),
                                       GROUP_EDIT_PARAM: group,
                                       GROUP_EDIT_SETTING_PARAM: name}))
            return None
        # S3 — number modal: an int / float scalar opens the number-input
        # widget (the oracle NumberSettingModal). The group + picked setting
        # ride the opening args so the child session-view bakes them onto the
        # modal-issue stash; the modal submit commits through set_scalar.
        if _is_number_spec(spec):
            import dataclasses as _dc

            from sb.domain.settings.panels import (
                GROUP_EDIT_PARAM,
                GROUP_EDIT_SETTING_PARAM,
            )
            from sb.kernel.panels.engine import open_panel
            from sb.spec.refs import PanelRef

            await open_panel(
                PanelRef("settings.group_edit_number"),
                _dc.replace(req, args={**dict(req.args),
                                       GROUP_EDIT_PARAM: group,
                                       GROUP_EDIT_SETTING_PARAM: name}))
            return None
        # S4 — free-text modal: a str-without-allowed_values scalar opens the
        # free-text-input widget (the oracle TextSettingModal). The group +
        # picked setting ride the opening args so the child session-view bakes
        # them onto the modal-issue stash; the modal submit commits through
        # set_scalar.
        if _is_text_spec(spec):
            import dataclasses as _dc

            from sb.domain.settings.panels import (
                GROUP_EDIT_PARAM,
                GROUP_EDIT_SETTING_PARAM,
            )
            from sb.kernel.panels.engine import open_panel
            from sb.spec.refs import PanelRef

            await open_panel(
                PanelRef("settings.group_edit_text"),
                _dc.replace(req, args={**dict(req.args),
                                       GROUP_EDIT_PARAM: group,
                                       GROUP_EDIT_SETTING_PARAM: name}))
            return None
        # S6 — the role-select widget is the last unported per-type widget
        # (routed separately from this epic).
        return Reply(
            SUCCESS,
            f"⚙️ The `{spec.value_type}` editor for `{group}.{name}` "
            f"ports in a later settings slice (S6 role select). The bool "
            f"toggle (S1), enum select (S2), number modal (S3), free-text "
            f"modal (S4), channel select (S5) and numeric-presets quick-set "
            f"(S7) are live now.")

    @handler("settings.group_edit_reset")
    async def group_edit_reset(req):
        """The windowed "Reset a setting…" select — restore the spec's
        default by clearing the explicit row (settings.clear_scalar; the
        oracle reset_setting path)."""
        from sb.domain.settings.ops import CLEAR_SCALAR
        from sb.domain.settings.panels import _group_edit_spec
        from sb.spec.outcomes import BLOCKED

        group, name = _group_edit_selection(req)
        if not group or not name:
            return Reply(SUCCESS, _GROUP_EDIT_EXPIRED)
        spec = _group_edit_spec(group, name)
        if spec is None:
            return Reply(BLOCKED, f"⚙️ Unknown setting `{group}.{name}`.")
        if not req.guild_id:
            return Reply(BLOCKED, "❌ Settings are per server — use this "
                                  "inside a server.")
        from sb.kernel import settings as ksettings

        key = ksettings.persisted_key(group, name)
        result = await _run_scalar_op(req, CLEAR_SCALAR, {"key": key})
        if getattr(result, "outcome", None) != SUCCESS:
            return Reply(
                getattr(result, "outcome", "error"),
                f"❌ Couldn't reset `{group}.{name}`: "
                f"{getattr(result, 'user_message', '') or 'write failed'}")
        await _refresh_group_edit(req, group)
        return Reply(
            SUCCESS,
            f"✅ `{group}.{name}` reset to its default "
            f"(`{spec.default!r}`).")

    @handler("settings.group_open_panel")
    async def group_open_panel(req):
        """The shipped Open-Panel button (subsystem_view.py
        _OpenRelatedPanelButton) — routes to the group's related cog panel.
        Non-hub groups have no dedicated operator panel in the port (the
        _GROUP_PANELS games arm never reaches this page), so this is the
        oracle's no-panel fallback: an honest pointer to the group's read
        controls. A dedicated route lands with the group's own panel
        slice."""
        from sb.domain.settings.panels import GROUP_EDIT_PARAM

        group = str(req.args.get(GROUP_EDIT_PARAM) or "")
        return Reply(
            SUCCESS,
            f"⚙️ `{group}` has no dedicated interactive panel yet — use the "
            f"Edit / Reset selects above, or the hub's diagnostics "
            f"(📋 Needs setup · ⚠️ Invalid settings · 🔗 Missing bindings).")

    # --- the ported enum-select edit widget (settings epic S2) --------------
    # The oracle build_enum_select_view (disbot/views/settings/edit_enum.py):
    # a windowed select of a str setting's declared allowed_values whose pick
    # wrote through the mutation pipeline. Here the chosen member commits
    # through the LIVE K7 settings.set_scalar lane (no new op) and the picker
    # refreshes in place. The group + setting ride the click's session-minted
    # args (GROUP_EDIT_PARAM / GROUP_EDIT_SETTING_PARAM).

    @handler("settings.group_edit_enum_pick")
    async def group_edit_enum_pick(req):
        """The windowed enum select — commit the chosen allowed value through
        settings.set_scalar. The value rides the ordinary select `values`
        round-trip (so an out-of-window pick resolves the same as a
        first-window one); the (group, setting) ride the minted-child args."""
        from sb.domain.settings.ops import SET_SCALAR
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
            _group_edit_spec,
            _is_enum_spec,
        )
        from sb.spec.outcomes import BLOCKED

        group = str(req.args.get(GROUP_EDIT_PARAM) or "")
        name = str(req.args.get(GROUP_EDIT_SETTING_PARAM) or "")
        values = tuple(req.args.get("values", ()) or ())
        chosen = str(values[0]) if values else ""
        if not group or not name:
            return Reply(SUCCESS, _GROUP_EDIT_EXPIRED)
        spec = _group_edit_spec(group, name)
        if spec is None or not _is_enum_spec(spec):
            return Reply(BLOCKED,
                         f"⚙️ `{group}.{name}` is not an enum setting.")
        allowed = tuple(str(v) for v in (spec.allowed_values or ()))
        if chosen not in allowed:
            return Reply(BLOCKED,
                         f"⚙️ `{chosen}` is not an allowed value for "
                         f"`{group}.{name}`.")
        if not req.guild_id:
            return Reply(BLOCKED, "❌ Settings are per server — use this "
                                  "inside a server.")
        from sb.kernel import settings as ksettings

        key = ksettings.persisted_key(group, name)
        result = await _run_scalar_op(req, SET_SCALAR,
                                      {"key": key, "value": chosen})
        if getattr(result, "outcome", None) != SUCCESS:
            return Reply(
                getattr(result, "outcome", "error"),
                f"❌ Couldn't update `{group}.{name}`: "
                f"{getattr(result, 'user_message', '') or 'write failed'}")
        await _refresh_group_edit_enum(req, group, name)
        return Reply(SUCCESS,
                     f"✅ `{group}.{name}` set to **{chosen}**.")

    @handler("settings.group_edit_enum_back")
    async def group_edit_enum_back(req):
        """↩ Back to settings — re-open the group's edit page (the group rides
        the click's args; the oracle enum view's back-to-parent). Never a
        strand: a missing group falls back to the honest expiry terminal."""
        import dataclasses as _dc

        from sb.domain.settings.panels import GROUP_EDIT_PARAM
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        group = str(req.args.get(GROUP_EDIT_PARAM) or "")
        if not group:
            return Reply(SUCCESS, _GROUP_EDIT_EXPIRED)
        await open_panel(
            PanelRef("settings.group_edit"),
            _dc.replace(req, args={**dict(req.args),
                                   GROUP_EDIT_PARAM: group}))
        return None

    # --- the ported channel-select edit widget (settings epic S5) -----------
    # The oracle ChannelSettingSelectView (disbot/views/settings/edit_channel.py):
    # a native ChannelSelect whose pick wrote the chosen channel id through the
    # audited mutation pipeline. Here that select is its own session-view child
    # (settings.group_edit_channel), rendered as a windowed provider-fed select
    # over the channel-directory roster (the port-frame convention); the chosen
    # channel id commits through the LIVE K7 settings.set_scalar lane (no new op)
    # and the picker refreshes in place. The group + setting ride the click's
    # session-minted args (GROUP_EDIT_PARAM / GROUP_EDIT_SETTING_PARAM).

    @handler("settings.group_edit_channel_pick")
    async def group_edit_channel_pick(req):
        """The windowed channel select — commit the chosen channel id through
        settings.set_scalar. The channel id rides the ordinary select `values`
        round-trip (so an out-of-window pick resolves the same as a first-window
        one); the (group, setting) ride the minted-child args. A non-numeric
        selection rejects without a write."""
        from sb.domain.settings.ops import SET_SCALAR
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
            _group_edit_spec,
            _is_channel_spec,
        )
        from sb.spec.outcomes import BLOCKED

        group = str(req.args.get(GROUP_EDIT_PARAM) or "")
        name = str(req.args.get(GROUP_EDIT_SETTING_PARAM) or "")
        values = tuple(req.args.get("values", ()) or ())
        chosen = str(values[0]) if values else ""
        if not group or not name:
            return Reply(SUCCESS, _GROUP_EDIT_EXPIRED)
        spec = _group_edit_spec(group, name)
        if spec is None or not _is_channel_spec(spec):
            return Reply(BLOCKED,
                         f"⚙️ `{group}.{name}` is not a channel setting.")
        if not chosen.isdigit():
            return Reply(BLOCKED,
                         f"⚙️ `{chosen}` is not a valid channel for "
                         f"`{group}.{name}`.")
        if not req.guild_id:
            return Reply(BLOCKED, "❌ Settings are per server — use this "
                                  "inside a server.")
        from sb.kernel import settings as ksettings

        key = ksettings.persisted_key(group, name)
        result = await _run_scalar_op(req, SET_SCALAR,
                                      {"key": key, "value": chosen})
        if getattr(result, "outcome", None) != SUCCESS:
            return Reply(
                getattr(result, "outcome", "error"),
                f"❌ Couldn't update `{group}.{name}`: "
                f"{getattr(result, 'user_message', '') or 'write failed'}")
        await _refresh_group_edit_channel(req, group, name)
        return Reply(SUCCESS,
                     f"✅ `{group}.{name}` set to <#{chosen}>.")

    @handler("settings.group_edit_channel_back")
    async def group_edit_channel_back(req):
        """↩ Back to settings — re-open the group's edit page (the group rides
        the click's args; the enum_back twin). Never a strand: a missing group
        falls back to the honest expiry terminal."""
        import dataclasses as _dc

        from sb.domain.settings.panels import GROUP_EDIT_PARAM
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        group = str(req.args.get(GROUP_EDIT_PARAM) or "")
        if not group:
            return Reply(SUCCESS, _GROUP_EDIT_EXPIRED)
        await open_panel(
            PanelRef("settings.group_edit"),
            _dc.replace(req, args={**dict(req.args),
                                   GROUP_EDIT_PARAM: group}))
        return None

    # --- the ported numeric-presets quick-set edit widget (settings epic S7) -
    # The oracle NumericPresetsView (disbot/views/settings/edit_number_presets.py):
    # a row of quick-set buttons (one per declared preset value) whose click wrote
    # the fixed value through the audited mutation pipeline. Here that widget is
    # its own session-view child (settings.group_edit_presets) rendered as static
    # preset-button slots relabelled per-setting by the render override; the
    # clicked slot's index rides session_action (the access_page precedent), the
    # handler maps it back onto spec.presets[index], and the value commits through
    # the LIVE K7 settings.set_scalar lane (no new op) and the widget refreshes in
    # place. The group + setting ride the click's session-minted args
    # (GROUP_EDIT_PARAM / GROUP_EDIT_SETTING_PARAM).

    @handler("settings.group_edit_presets_pick")
    async def group_edit_presets_pick(req):
        """A quick-set preset button — commit its declared preset value through
        settings.set_scalar. The clicked slot's index rides session_action
        (pval_<i>); the handler maps it back onto the picked SettingSpec's
        `presets` tuple (so the fixed value is re-derived from the spec, never
        trusted from the wire); the (group, setting) ride the minted-child args.
        A stale slot beyond the declared presets rejects without a write."""
        from sb.domain.settings.ops import SET_SCALAR
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
            _group_edit_spec,
            _is_presets_spec,
        )
        from sb.spec.outcomes import BLOCKED

        group = str(req.args.get(GROUP_EDIT_PARAM) or "")
        name = str(req.args.get(GROUP_EDIT_SETTING_PARAM) or "")
        if not group or not name:
            return Reply(SUCCESS, _GROUP_EDIT_EXPIRED)
        spec = _group_edit_spec(group, name)
        if spec is None or not _is_presets_spec(spec):
            return Reply(BLOCKED,
                         f"⚙️ `{group}.{name}` is not a numeric-presets "
                         f"setting.")
        if not req.guild_id:
            return Reply(BLOCKED, "❌ Settings are per server — use this "
                                  "inside a server.")
        # the clicked slot id (pval_<i>) → the preset index; re-derive the value
        # from the spec (never the wire) so a stale/forged id can't write an
        # arbitrary value.
        action = str(req.args.get("session_action") or "")
        try:
            index = int(action.rsplit("_", 1)[1])
        except (ValueError, IndexError):
            return Reply(SUCCESS, _GROUP_EDIT_EXPIRED)
        presets = tuple(getattr(spec, "presets", ()) or ())
        if not 0 <= index < len(presets):
            return Reply(BLOCKED,
                         f"⚙️ That preset is no longer available for "
                         f"`{group}.{name}`.")
        value = presets[index]
        from sb.kernel import settings as ksettings

        key = ksettings.persisted_key(group, name)
        result = await _run_scalar_op(req, SET_SCALAR,
                                      {"key": key, "value": str(value)})
        if getattr(result, "outcome", None) != SUCCESS:
            return Reply(
                getattr(result, "outcome", "error"),
                f"❌ Couldn't update `{group}.{name}`: "
                f"{getattr(result, 'user_message', '') or 'write failed'}")
        await _refresh_group_edit_presets(req, group, name)
        return Reply(SUCCESS,
                     f"✅ `{group}.{name}` set to **{value!r}**.")

    @handler("settings.group_edit_presets_back")
    async def group_edit_presets_back(req):
        """↩ Back to settings — re-open the group's edit page (the group rides
        the click's args; the channel_back twin). Never a strand: a missing group
        falls back to the honest expiry terminal."""
        import dataclasses as _dc

        from sb.domain.settings.panels import GROUP_EDIT_PARAM
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        group = str(req.args.get(GROUP_EDIT_PARAM) or "")
        if not group:
            return Reply(SUCCESS, _GROUP_EDIT_EXPIRED)
        await open_panel(
            PanelRef("settings.group_edit"),
            _dc.replace(req, args={**dict(req.args),
                                   GROUP_EDIT_PARAM: group}))
        return None

    # --- the ported number-modal edit widget (settings epic S3) -------------
    # The oracle NumberSettingModal (disbot/views/settings/edit_number.py): a
    # one-input modal for int / float scalars whose submit coerced + validated
    # the typed value and wrote through the mutation pipeline. Here the modal is
    # a G-10 ModalSpec on the settings.group_edit_number child; the submit
    # re-enters through the frozen MODAL adapter with the (group, setting)
    # restored from the kernel modal-args stash (the opening click's
    # session-minted args — the ai settings_number_submit precedent). The value
    # coerces + range-validates through the settings-service coerce_value seam
    # (bounds + type — the read path's own coercer) and commits through the LIVE
    # K7 settings.set_scalar lane (no new op); an invalid / out-of-range entry
    # rejects without a write.

    @handler("settings.group_edit_number_submit")
    async def group_edit_number_submit(req):
        """The number form's SUBMIT (the oracle NumberSettingModal.on_submit):
        coerce + range-validate the typed input against the picked SettingSpec,
        then commit through settings.set_scalar. The (group, setting) arrive
        through the kernel modal-args stash (a stash miss falls to the honest
        expiry terminal); a non-numeric / out-of-range value rejects without a
        write."""
        from sb.domain.settings.ops import SET_SCALAR
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
            _group_edit_spec,
            _is_number_spec,
        )
        from sb.spec.outcomes import BLOCKED

        group = str(req.args.get(GROUP_EDIT_PARAM) or "")
        name = str(req.args.get(GROUP_EDIT_SETTING_PARAM) or "")
        if not group or not name:
            return Reply(SUCCESS, _GROUP_EDIT_EXPIRED)
        spec = _group_edit_spec(group, name)
        if spec is None or not _is_number_spec(spec):
            return Reply(BLOCKED,
                         f"⚙️ `{group}.{name}` is not a number setting.")
        if not req.guild_id:
            return Reply(BLOCKED, "❌ Settings are per server — use this "
                                  "inside a server.")
        raw = str(req.args.get("number_value") or "").strip()
        from sb.domain.settings.service import coerce_value

        value, ok, diags = coerce_value(spec, raw)
        if not ok:
            # the shipped NumberSettingModal coercion / validation reject
            # (SettingsCoercionError / SettingsValidationError) — no write.
            return Reply(
                BLOCKED,
                f"❌ Couldn't update `{group}.{name}`: cannot coerce "
                f"value={raw!r} to {spec.value_type} "
                f"({'; '.join(diags) or 'invalid value'}).")
        from sb.kernel import settings as ksettings

        key = ksettings.persisted_key(group, name)
        result = await _run_scalar_op(req, SET_SCALAR,
                                      {"key": key, "value": str(value)})
        if getattr(result, "outcome", None) != SUCCESS:
            return Reply(
                getattr(result, "outcome", "error"),
                f"❌ Couldn't update `{group}.{name}`: "
                f"{getattr(result, 'user_message', '') or 'write failed'}")
        await _refresh_group_edit_number(req, group, name)
        return Reply(SUCCESS,
                     f"✅ `{group}.{name}` set to **{value!r}**.")

    @handler("settings.group_edit_number_back")
    async def group_edit_number_back(req):
        """↩ Back to settings — re-open the group's edit page (the group rides
        the click's args; the enum_back twin). Never a strand: a missing group
        falls back to the honest expiry terminal."""
        import dataclasses as _dc

        from sb.domain.settings.panels import GROUP_EDIT_PARAM
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        group = str(req.args.get(GROUP_EDIT_PARAM) or "")
        if not group:
            return Reply(SUCCESS, _GROUP_EDIT_EXPIRED)
        await open_panel(
            PanelRef("settings.group_edit"),
            _dc.replace(req, args={**dict(req.args),
                                   GROUP_EDIT_PARAM: group}))
        return None

    # --- the ported free-text-modal edit widget (settings epic S4) ----------
    # The oracle TextSettingModal (disbot/views/settings/edit_text.py): a
    # one-input free-text modal for str-without-allowed_values scalars whose
    # submit wrote the typed string through the mutation pipeline. Here the
    # modal is a G-10 ModalSpec on the settings.group_edit_text child; the
    # submit re-enters through the frozen MODAL adapter with the (group, setting)
    # restored from the kernel modal-args stash (the S3 number precedent). The
    # submitted string is validated (non-empty + the declared bounds max-length
    # per the SettingSpec — coerce_value does NOT apply str bounds, so the
    # length gate lives here) then commits through the LIVE K7
    # settings.set_scalar lane (no new op); an empty / over-length entry rejects
    # without a write.

    @handler("settings.group_edit_text_submit")
    async def group_edit_text_submit(req):
        """The text form's SUBMIT (the oracle TextSettingModal.on_submit):
        validate the typed string against the picked SettingSpec (non-empty +
        the declared max-length bound), then commit through settings.set_scalar.
        The (group, setting) arrive through the kernel modal-args stash (a stash
        miss falls to the honest expiry terminal); an empty / over-length value
        rejects without a write."""
        from sb.domain.settings.ops import SET_SCALAR
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
            _group_edit_spec,
            _is_text_spec,
        )
        from sb.spec.outcomes import BLOCKED

        group = str(req.args.get(GROUP_EDIT_PARAM) or "")
        name = str(req.args.get(GROUP_EDIT_SETTING_PARAM) or "")
        if not group or not name:
            return Reply(SUCCESS, _GROUP_EDIT_EXPIRED)
        spec = _group_edit_spec(group, name)
        if spec is None or not _is_text_spec(spec):
            return Reply(BLOCKED,
                         f"⚙️ `{group}.{name}` is not a free-text setting.")
        if not req.guild_id:
            return Reply(BLOCKED, "❌ Settings are per server — use this "
                                  "inside a server.")
        # the shipped TextSettingModal stored the value verbatim; keep it as
        # typed (templates carry meaningful internal whitespace).
        raw = str(req.args.get("text_value") or "")
        # non-empty — the widget requires a value (use Reset to clear a setting;
        # the S0 reset select clears the explicit row through clear_scalar).
        if not raw.strip():
            return Reply(
                BLOCKED,
                f"❌ Couldn't update `{group}.{name}`: the value can't be "
                f"empty (use **Reset** on the edit page to clear it).")
        # declared max-length: str bounds are the single-element (max_len,).
        bounds = getattr(spec, "bounds", None)
        if bounds and len(bounds) >= 1 and isinstance(bounds[0], int):
            max_len = bounds[0]
            if len(raw) > max_len:
                return Reply(
                    BLOCKED,
                    f"❌ Couldn't update `{group}.{name}`: value is too long "
                    f"({len(raw)} > {max_len} characters).")
        from sb.domain.settings.service import coerce_value

        value, ok, diags = coerce_value(spec, raw)
        if not ok:
            # the shipped TextSettingModal coercion reject (SettingsMutationError)
            # — no write. For a free-text str this is a defensive belt (str
            # coercion is identity); an allowed_values guard would trip here.
            return Reply(
                BLOCKED,
                f"❌ Couldn't update `{group}.{name}`: cannot coerce "
                f"value={raw!r} to {spec.value_type} "
                f"({'; '.join(diags) or 'invalid value'}).")
        from sb.kernel import settings as ksettings

        key = ksettings.persisted_key(group, name)
        result = await _run_scalar_op(req, SET_SCALAR,
                                      {"key": key, "value": str(value)})
        if getattr(result, "outcome", None) != SUCCESS:
            return Reply(
                getattr(result, "outcome", "error"),
                f"❌ Couldn't update `{group}.{name}`: "
                f"{getattr(result, 'user_message', '') or 'write failed'}")
        await _refresh_group_edit_text(req, group, name)
        return Reply(SUCCESS,
                     f"✅ `{group}.{name}` set to **{value!r}**.")

    @handler("settings.group_edit_text_back")
    async def group_edit_text_back(req):
        """↩ Back to settings — re-open the group's edit page (the group rides
        the click's args; the number_back twin). Never a strand: a missing group
        falls back to the honest expiry terminal."""
        import dataclasses as _dc

        from sb.domain.settings.panels import GROUP_EDIT_PARAM
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        group = str(req.args.get(GROUP_EDIT_PARAM) or "")
        if not group:
            return Reply(SUCCESS, _GROUP_EDIT_EXPIRED)
        await open_panel(
            PanelRef("settings.group_edit"),
            _dc.replace(req, args={**dict(req.args),
                                   GROUP_EDIT_PARAM: group}))
        return None


_register()


def ensure_handler_refs() -> None:
    _register()

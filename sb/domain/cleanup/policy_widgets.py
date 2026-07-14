"""The 🧹 Cleanup Policies flow handlers + option providers — the
oracle ``disbot/views/cleanup/policy_panel.py`` @9776401 builder/remove
callbacks on this engine's page-swap posture (the ai policy/behavior/
tools precedent: a select pick re-opens the next page via ``open_panel``
carrying the flow state in session args; the oracle chained ephemeral
messages instead — same steps, same copy, ledgered idiom).

Flow state args (``pol_``-prefixed so merged session args never
collide): ``pol_scope``/``pol_target``/``pol_label`` name the picked
scope; ``pol_div``/``pol_dfc``/``pol_das`` carry the explicit column
values the preview + apply read; ``pol_level`` carries the preset name
for the ack byte (absent for custom — the preview names it back via
``level_for_columns``, the oracle posture).

Authority: every action/selector in the flow declares
``audience_tier="administrator"`` (the oracle's ``interaction_is_admin``
re-check at each mutation surface, expressed in the engine's two-lane
authority grammar) with the K7 governance pipeline's authority leg as
the infrastructure backstop — the oracle's own layering.

Registered at MODULE IMPORT (the BUG A rule).
"""

from __future__ import annotations

import dataclasses
import logging

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

logger = logging.getLogger("sb.domain.cleanup.policy_widgets")

__all__ = ["ensure_policy_widget_refs"]

#: the oracle sentinel for the level select's Custom… option.
CUSTOM_VALUE = "__custom__"

#: Discord select hard limit (oracle _MAX_REMOVE_OPTIONS).
MAX_REMOVE_OPTIONS = 25

#: duration choices for the custom builder — the oracle table verbatim
#: (all within 0..MAX_DELETE_AFTER_SECONDS, so no typing or
#: range-checking is needed).
DURATION_OPTIONS: tuple[tuple[int, str], ...] = (
    (0, "Instant (0s)"),
    (2, "2 seconds"),
    (5, "5 seconds"),
    (10, "10 seconds"),
    (30, "30 seconds"),
    (60, "1 minute"),
    (120, "2 minutes"),
    (300, "5 minutes"),
)
DURATION_LABELS: dict[int, str] = dict(DURATION_OPTIONS)

#: the custom builder's defaults (oracle _CustomLevelView.__init__).
CUSTOM_DEFAULTS = {"pol_das": "10", "pol_div": "yes", "pol_dfc": "no"}

_NEEDS_GUILD = "❌ Cleanup policies can only be configured inside a server."


def _picked(req) -> str:
    values = tuple(req.args.get("values", ()) or ())
    return str(values[0]) if values else ""


async def _open_page(req, panel_id: str, extra: dict) -> None:
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    args = {**dict(req.args or {}), **extra}
    await open_panel(PanelRef(panel_id), dataclasses.replace(req, args=args))


def _flow_columns(req) -> tuple[bool, bool, int]:
    """The staged explicit columns (preview + apply read the SAME args)."""
    div = str(req.args.get("pol_div") or "yes") == "yes"
    dfc = str(req.args.get("pol_dfc") or "no") == "yes"
    try:
        das = int(str(req.args.get("pol_das") or "10"))
    except ValueError:
        das = 10
    return div, dfc, das


async def _channel_label(guild_id: int, channel_id: int) -> str:
    """``#name`` via the roster port (oracle ``#{picked.name}``);
    mention degrade when the roster is uninstalled."""
    from sb.domain.cleanup import policy_service as svc

    names = await svc.scope_labels(int(guild_id))
    name = names.channels.get(int(channel_id))
    return f"#{name}" if name is not None else f"<#{channel_id}>"


async def _category_label(guild_id: int, category_id: int) -> str:
    """The bare category NAME (oracle ``picked.name``); raw-id degrade."""
    from sb.domain.cleanup import policy_service as svc

    names = await svc.scope_labels(int(guild_id))
    name = names.categories.get(int(category_id))
    return str(name) if name is not None else str(category_id)


# --- the builder flow picks -----------------------------------------------------------


async def policies_scope_pick(req) -> Reply | None:
    """_ScopeSelect.callback — guild reveals the level select directly;
    category/channel route through their target pick first."""
    if not req.guild_id:
        return Reply(BLOCKED, _NEEDS_GUILD)
    scope = _picked(req)
    if scope == "guild":
        await _open_page(req, "cleanup.policies_level", {
            "pol_scope": "guild", "pol_target": str(int(req.guild_id)),
            "pol_label": "Guild default"})
        return None
    if scope == "category":
        await _open_page(req, "cleanup.policies_category_pick", {})
        return None
    await _open_page(req, "cleanup.policies_channel_pick", {})
    return None


async def policies_channel_pick(req) -> Reply | None:
    """_ChannelPickSelect.callback — hand the picked channel to the
    level select (label = the oracle ``#{picked.name}`` byte)."""
    if not req.guild_id:
        return Reply(BLOCKED, _NEEDS_GUILD)
    target = _picked(req)
    label = await _channel_label(int(req.guild_id), int(target or 0))
    await _open_page(req, "cleanup.policies_level", {
        "pol_scope": "channel", "pol_target": target, "pol_label": label})
    return None


async def policies_category_pick(req) -> Reply | None:
    """_CategoryPickSelect.callback — label = ``Category {name}``
    (the oracle level-select label byte)."""
    if not req.guild_id:
        return Reply(BLOCKED, _NEEDS_GUILD)
    target = _picked(req)
    name = await _category_label(int(req.guild_id), int(target or 0))
    await _open_page(req, "cleanup.policies_level", {
        "pol_scope": "category", "pol_target": target,
        "pol_label": f"Category {name}"})
    return None


async def policies_level_pick(req) -> Reply | None:
    """_LevelSelect.callback — Custom… opens the select-driven custom
    builder (oracle defaults after=10/invalid=yes/failed=no); a preset
    stages its column values and opens the dry-run preview page."""
    from sb.domain.setup.cleanup import LEVELS

    if not req.guild_id:
        return Reply(BLOCKED, _NEEDS_GUILD)
    level = _picked(req)
    if level == CUSTOM_VALUE:
        await _open_page(req, "cleanup.policies_custom", dict(CUSTOM_DEFAULTS))
        return None
    cols = LEVELS.get(level)
    if cols is None:
        return Reply(BLOCKED, "Could not build the preview — see logs.")
    await _open_page(req, "cleanup.policies_preview", {
        "pol_level": level,
        "pol_div": "yes" if cols["delete_invalid_commands"] else "no",
        "pol_dfc": "yes" if cols["delete_failed_commands"] else "no",
        "pol_das": str(int(cols["delete_after_seconds"]))})
    return None


# --- the custom builder (three pickers + preview) ---------------------------------------


async def policies_custom_after(req) -> Reply | None:
    """_DeleteAfterSelect.callback — rebuild the builder page with the
    changed value so the selects show the new state (oracle
    ``_CustomLevelView.update``)."""
    await _open_page(req, "cleanup.policies_custom",
                     {"pol_das": _picked(req) or "10"})
    return None


async def policies_custom_invalid(req) -> Reply | None:
    await _open_page(req, "cleanup.policies_custom",
                     {"pol_div": _picked(req) or "yes"})
    return None


async def policies_custom_failed(req) -> Reply | None:
    await _open_page(req, "cleanup.policies_custom",
                     {"pol_dfc": _picked(req) or "no"})
    return None


async def policies_custom_preview(req) -> Reply | None:
    """_CustomPreviewButton.callback — route the staged explicit columns
    through the SAME dry-run preview page as the presets (no
    ``pol_level``: the preview names a preset-matching tuple back via
    ``level_for_columns``, else "Custom" — the oracle posture)."""
    if not req.guild_id:
        return Reply(BLOCKED, _NEEDS_GUILD)
    args = {k: str(req.args.get(k) or v) for k, v in CUSTOM_DEFAULTS.items()}
    args.pop("pol_level", None)
    await _open_page(req, "cleanup.policies_preview", args)
    return None


# --- confirm + apply ---------------------------------------------------------------------


async def policies_apply(req) -> Reply:
    """_ConfirmApplyView.btn_apply — the audited apply through the K7
    ``governance.set_cleanup`` pipeline (row + governance audit in one
    txn, post-commit cache invalidation). Ack/refusal bytes verbatim."""
    from sb.domain.cleanup import policy_service as svc

    if not req.guild_id:
        return Reply(BLOCKED, _NEEDS_GUILD)
    scope_type = str(req.args.get("pol_scope") or "")
    target = str(req.args.get("pol_target") or "")
    if scope_type not in svc.CLEANUP_SCOPE_TYPES or not target.isdigit():
        # a stale/foreign page open leaves the args bare — the guard
        # answers, never a write (the policy_mode_submit posture).
        return Reply(BLOCKED, "❌ Could not apply the policy — see logs.")
    div, dfc, das = _flow_columns(req)
    label = str(req.args.get("pol_label") or "")
    level = (str(req.args.get("pol_level") or "")
             or svc.level_for_columns(delete_invalid_commands=div,
                                      delete_failed_commands=dfc,
                                      delete_after_seconds=das)
             or svc.CUSTOM_LEVEL_LABEL)
    try:
        result = await svc.apply_cleanup_columns(
            req, scope_type, int(target),
            delete_invalid_commands=div, delete_failed_commands=dfc,
            delete_after_seconds=das)
    except ValueError as exc:
        # the oracle GovernanceError branch's shape (validation refusal).
        return Reply(BLOCKED, f"❌ Could not apply: {exc}")
    except Exception:  # noqa: BLE001 — surface a clean error, never crash
        logger.exception("cleanup apply failed")
        return Reply(BLOCKED, "❌ Could not apply the policy — see logs.")
    if getattr(result, "outcome", None) != SUCCESS:
        return Reply(getattr(result, "outcome", BLOCKED),
                     "❌ Could not apply: "
                     f"{getattr(result, 'user_message', None) or 'write failed'}")
    return Reply(SUCCESS,
                 f"✅ Applied `{level}` to **{label}**. "
                 "Resolution updates immediately.")


async def policies_cancel(req) -> Reply:
    """_ConfirmApplyView.btn_cancel — the byte verbatim."""
    return Reply(SUCCESS, "Cancelled — nothing was written.")


# --- the remove flow ----------------------------------------------------------------------


async def policies_remove_route(req) -> Reply | None:
    """btn_remove — the no-rows early answer (byte verbatim), else the
    remove-select page."""
    from sb.domain.cleanup import policy_service as svc

    if not req.guild_id:
        return Reply(BLOCKED, _NEEDS_GUILD)
    diag = await svc.collect_cleanup_diagnostics(int(req.guild_id))
    if not diag.rows:
        return Reply(SUCCESS,
                     "There are no stored cleanup overrides to remove — "
                     "every scope already uses the inherited default.")
    await _open_page(req, "cleanup.policies_remove", {})
    return None


async def policies_remove_pick(req) -> Reply:
    """_RemoveSelect.callback — parse ``scope_type:scope_id`` (keyed by
    the LITERAL stored id so legacy/stale rows clear), the audited
    remove, the removed/already-gone ack bytes verbatim."""
    from sb.domain.cleanup import policy_service as svc

    if not req.guild_id:
        return Reply(BLOCKED, _NEEDS_GUILD)
    scope_type, _, raw_id = _picked(req).partition(":")
    try:
        scope_id = int(raw_id)
    except ValueError:
        return Reply(BLOCKED, "Could not parse that selection — try again.")
    try:
        result = await svc.remove_cleanup_change(req, scope_type, scope_id)
    except ValueError as exc:
        return Reply(BLOCKED, f"❌ Could not remove: {exc}")
    except Exception:  # noqa: BLE001 — surface a clean error, never crash
        logger.exception("cleanup remove failed")
        return Reply(BLOCKED, "❌ Could not remove the policy — see logs.")
    if getattr(result, "outcome", None) != SUCCESS:
        return Reply(getattr(result, "outcome", BLOCKED),
                     "❌ Could not remove: "
                     f"{getattr(result, 'user_message', None) or 'write failed'}")
    removed = bool(((getattr(result, "after", None) or {})
                    .get("record") or {}).get("removed"))
    if removed:
        return Reply(SUCCESS,
                     "✅ Removed the override — it now inherits from its "
                     "parent scope. Resolution updates immediately.")
    return Reply(SUCCESS, "ℹ️ That row was already gone — nothing to remove.")


# --- option providers -----------------------------------------------------------------------


async def policies_category_options(ctx):
    """The category pick roster (the ai policy_category_options lane —
    the D-0070(a) ledgered string-select posture for category scopes)."""
    from sb.domain.cleanup import policy_service as svc

    names = await svc.scope_labels(int(ctx.guild_id or 0))
    return tuple({"label": str(name)[:100], "value": str(cid)}
                 for cid, name in sorted(names.categories.items(),
                                         key=lambda kv: kv[1].lower()))


async def policies_level_options(ctx):
    """_level_options — one option per preset (description = the column
    summary byte) + the ⚙️ Custom… option, verbatim."""
    from sb.domain.setup.cleanup import LEVELS

    options = [
        {"label": name, "value": name,
         "description": (
             f"after={cols['delete_after_seconds']}s · "
             f"invalid={'yes' if cols['delete_invalid_commands'] else 'no'} · "
             f"failed={'yes' if cols['delete_failed_commands'] else 'no'}")}
        for name, cols in LEVELS.items()
    ]
    options.append({
        "label": "Custom…", "value": CUSTOM_VALUE, "emoji": "⚙️",
        "description": "Tune delete-after seconds + which commands are "
                       "deleted."})
    return tuple(options)


async def policies_after_options(ctx):
    """_DeleteAfterSelect — the fixed duration menu, current staged
    value pre-selected (the oracle ``default=(seconds == current)``)."""
    try:
        current = int(str((ctx.params or {}).get("pol_das") or "10"))
    except ValueError:
        current = 10
    return tuple({"label": label, "value": str(seconds),
                  "default": seconds == current}
                 for seconds, label in DURATION_OPTIONS)


def _yes_no_options(current_yes: bool):
    return ({"label": "Yes", "value": "yes", "default": current_yes},
            {"label": "No", "value": "no", "default": not current_yes})


async def policies_invalid_options(ctx):
    current = str((ctx.params or {}).get("pol_div") or "yes") == "yes"
    return _yes_no_options(current)


async def policies_failed_options(ctx):
    current = str((ctx.params or {}).get("pol_dfc") or "no") == "yes"
    return _yes_no_options(current)


async def policies_remove_options(ctx):
    """_remove_options — one option per stored row, flagging legacy /
    stale rows (label/description bytes + truncation verbatim; the
    25-option Discord cap)."""
    from sb.domain.cleanup import policy_service as svc

    diag = await svc.collect_cleanup_diagnostics(int(ctx.guild_id or 0))
    options = []
    for row in diag.rows[:MAX_REMOVE_OPTIONS]:
        suffix = ""
        if row.is_ineffective:
            suffix = " — ⚠️ legacy/ineffective"
        elif row.is_stale:
            suffix = " — ⚠️ scope deleted"
        options.append({
            "label": f"{row.target_label} ({row.display_level}){suffix}"[:100],
            "value": f"{row.scope_type}:{row.scope_id}",
            "description": (
                f"after={row.delete_after_seconds}s · "
                f"invalid={'yes' if row.delete_invalid_commands else 'no'} · "
                f"failed={'yes' if row.delete_failed_commands else 'no'}"
            )[:100]})
    return tuple(options)


# --- registration — MODULE IMPORT (BUG A rule) -----------------------------------------------

_HANDLERS = (
    ("cleanup.policies_scope_pick", policies_scope_pick),
    ("cleanup.policies_channel_pick", policies_channel_pick),
    ("cleanup.policies_category_pick", policies_category_pick),
    ("cleanup.policies_level_pick", policies_level_pick),
    ("cleanup.policies_custom_after", policies_custom_after),
    ("cleanup.policies_custom_invalid", policies_custom_invalid),
    ("cleanup.policies_custom_failed", policies_custom_failed),
    ("cleanup.policies_custom_preview", policies_custom_preview),
    ("cleanup.policies_apply", policies_apply),
    ("cleanup.policies_cancel", policies_cancel),
    ("cleanup.policies_remove_route", policies_remove_route),
    ("cleanup.policies_remove_pick", policies_remove_pick),
)

_PROVIDERS = (
    ("cleanup.policies_category_options", policies_category_options),
    ("cleanup.policies_level_options", policies_level_options),
    ("cleanup.policies_after_options", policies_after_options),
    ("cleanup.policies_invalid_options", policies_invalid_options),
    ("cleanup.policies_failed_options", policies_failed_options),
    ("cleanup.policies_remove_options", policies_remove_options),
)


def _register() -> None:
    from sb.spec.refs import (
        HandlerRef,
        ProviderRef,
        handler,
        is_registered,
        provider,
    )

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)
    for name, fn in _PROVIDERS:
        if not is_registered(ProviderRef(name)):
            provider(name)(fn)


_register()


def ensure_policy_widget_refs() -> None:
    _register()

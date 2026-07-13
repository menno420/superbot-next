"""The cleanup settings edit/reset MUTATION widgets — the shipped
SubsystemSettingsView S6/S7 flow for the cleanup schema
(views/settings/subsystem_view.py `dispatch_edit_setting` +
edit_number_presets/reset_button @9776401), ported onto the K7
`settings.set_scalar` op (the ONE audited write path to the `settings`
table — DB write + audit in one transaction, advisory ``settings.changed``
after commit; sb/domain/settings/ops.py). The sb/domain/ai/
settings_widgets.py precedent, trimmed to the roster cleanup declares:
ONE int scalar with the ``numeric_presets`` hint, so only the presets
widget page (+ its Override… G-10 number form) and the reset lane exist —
there is no bool/enum/free-text cleanup scalar to dispatch to.

Ack spelling: the shipped acks printed ``{subsystem}.{spec.name}``
(``cleanup.spam_window_seconds``); the page's Scalar field and the select
option bytes render the bare ``spec.name`` (the oracle
_resolve_settings_block/S6 roster bytes) — our acks print the ONE
spelling the page already renders, the bare name (the VERDICT 009 AIP-03
single-spelling rule the ai port ledgered).

* numeric_presets + presets → the NumericPresetsView page (one button per
  preset, current highlighted primary) — ``✅ Updated … (was …)``
* Override… (presets page)  → the shipped NumberSettingModal twin (G-10;
  the submit re-enters through the frozen modal adapter) —
  ``✅ Updated … (was …)``
* reset                     → write the declared default —
  ``✅ Reset `<name>` to default = …``

After a write the settings page embed refreshes in place best-effort (the
shipped `_refresh_parent` posture). Registered at MODULE IMPORT (the BUG A
rule).
"""

from __future__ import annotations

import dataclasses
import logging

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.spec.outcomes import SUCCESS

logger = logging.getLogger("sb.domain.cleanup.settings_widgets")

__all__ = ["ensure_widget_refs", "spec_for_name"]

_SUBSYSTEM = "cleanup"

#: shipped guard bytes (edit_number_presets / reset_button write paths).
_NEEDS_GUILD_RESET = "❌ Reset requires a guild context."
_NEEDS_GUILD_EDIT = "❌ Edit requires a guild context."


def spec_for_name(name: str):
    """The shipped-page SettingSpec for one spec.name (the select option
    values are the shipped ``spec.name`` strings — the oracle S6 roster)."""
    from sb.domain.cleanup.settings_schema import SHIPPED_CLEANUP_SETTINGS

    for spec in SHIPPED_CLEANUP_SETTINGS:
        if spec.name == name:
            return spec
    return None


async def current_value(guild_id: int, spec):
    """The shipped `resolve_setting` read (falls back to the declared
    default — the dispatcher's `current = spec.default` posture)."""
    from sb.kernel import settings as ksettings

    try:
        value = await ksettings.resolve(guild_id, _SUBSYSTEM, spec.name)
    except LookupError:
        return spec.default
    if isinstance(value, str) and str(spec.value_type) != "str":
        from sb.domain.settings.service import coerce_value

        coerced, ok, _diag = coerce_value(spec, value)
        return coerced if ok else spec.default
    return value


async def _write_setting(req, spec, value):
    """One audited write through the K7 `settings.set_scalar` op (the
    shipped SettingsMutationPipeline lane — the ai widgets' seam)."""
    from sb.kernel import settings as ksettings
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    key = ksettings.persisted_key(_SUBSYSTEM, spec.name)
    return await engine.run(
        WorkflowRef("settings.set_scalar"),
        ctx_from_request(req, {
            "key": key,
            "value": str(value),
            "subsystem": _SUBSYSTEM,
            "name": spec.name,
        }))


async def _refresh_settings_page(req) -> None:
    """Best-effort in-place refresh of the settings page embed after a
    write landed (the shipped `_refresh_parent` soft-fail posture)."""
    try:
        from sb.kernel.panels.engine import refresh_session_view

        message = getattr(req.origin, "message", None)
        message_key = str(getattr(message, "id", "") or "")
        if not message_key:
            return
        await refresh_session_view(req, message_key=message_key,
                                   params=dict(req.args or {}))
    except Exception:  # noqa: BLE001 — the confirmation already rendered
        logger.debug("cleanup settings page refresh failed", exc_info=True)


def _picked(req) -> str:
    values = tuple(req.args.get("values", ()) or ())
    return str(values[0]) if values else ""


def _in_transaction_prior(result, spec, fallback):
    """Prefer the IN-TRANSACTION prior the write leg returned over the
    pre-write read (the #160 codex-P3 posture the ai widgets share)."""
    prior_raw = ((result.before or {}).get("write_scalar") or {}).get("value")
    if prior_raw is None:
        return fallback
    from sb.domain.settings.service import coerce_value

    coerced, ok, _diag = coerce_value(spec, str(prior_raw))
    return coerced if ok else spec.default


# --- the settings-page select rows -------------------------------------------------


async def settings_edit_route(req) -> Reply | None:
    """The "Edit a setting…" pick — the shipped dispatch_edit_setting.
    Every declared cleanup scalar is numeric_presets-hinted, so the only
    live branch opens the presets widget page."""
    name = _picked(req)
    spec = spec_for_name(name)
    if spec is None:
        # shipped: f"❌ Unknown setting `{subsystem}.{name}`." — bare name
        # here (the AIP-03 single-spelling rule, module doc).
        return Reply(SUCCESS, f"❌ Unknown setting `{name}`.")
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    args = {**dict(req.args or {}), "setting": spec.name}
    await open_panel(PanelRef("cleanup.settings_edit_presets"),
                     dataclasses.replace(req, args=args))
    return None


async def settings_reset_route(req) -> Reply:
    """The "Reset a setting…" pick — the shipped reset_button
    (functionally set_value(spec.default) through the same audited lane)."""
    name = _picked(req)
    spec = spec_for_name(name)
    if spec is None:
        return Reply(SUCCESS, f"❌ Unknown setting `{name}`.")
    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_RESET)
    result = await _write_setting(req, spec, spec.default)
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     f"❌ Couldn't reset `{name}`: "
                     f"{result.user_message or 'write failed'}.")
    await _refresh_settings_page(req)
    return Reply(SUCCESS,
                 f"✅ Reset `{name}` to default = `{spec.default!r}`.")


# --- the presets widget page --------------------------------------------------------


async def settings_preset_pick(req) -> Reply:
    """One preset button on the numeric-presets widget (shipped
    edit_number_presets._write_preset_value) — the slot index maps into
    the spec's declared preset roster."""
    name = str(req.args.get("setting") or "")
    spec = spec_for_name(name)
    if spec is None or not spec.presets:
        return Reply(SUCCESS, f"❌ Unknown setting `{name}`.")
    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_EDIT)
    action = str(req.args.get("session_action") or "")
    if not action.startswith("cl_preset_"):
        return Reply(SUCCESS, f"❌ Unknown setting `{name}`.")
    try:
        index = int(action.rsplit("_", 1)[1])
        value = tuple(spec.presets)[index]
    except (ValueError, IndexError):
        return Reply(SUCCESS, f"❌ Unknown setting `{name}`.")
    old = await current_value(int(req.guild_id), spec)
    result = await _write_setting(req, spec, value)
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     f"❌ Couldn't update `{name}`: "
                     f"{result.user_message or 'write failed'}.")
    old = _in_transaction_prior(result, spec, old)
    await _refresh_settings_page(req)
    return Reply(SUCCESS,
                 f"✅ Updated `{name}` = `{value!r}` (was `{old!r}`).")


async def settings_number_submit(req) -> Reply:
    """The Override… form's SUBMIT (shipped NumberSettingModal.on_submit):
    strip → coerce/validate against the picked SettingSpec (bounds ride
    the same coercer the read path uses) → the audited write. The
    `setting` param arrives through the kernel modal-args stash (the
    opening click's session args)."""
    name = str(req.args.get("setting") or "")
    spec = spec_for_name(name)
    if spec is None:
        return Reply(SUCCESS, f"❌ Unknown setting `{name}`.")
    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_EDIT)
    raw = str(req.args.get("new_value") or "").strip()
    from sb.domain.settings.service import coerce_value

    value, ok, diags = coerce_value(spec, raw)
    if not ok:
        return Reply(SUCCESS,
                     f"❌ Couldn't update `{name}`: cannot coerce "
                     f"value={raw!r} to {spec.value_type} "
                     f"({'; '.join(diags) or 'invalid value'}).")
    old = await current_value(int(req.guild_id), spec)
    result = await _write_setting(req, spec, value)
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     f"❌ Couldn't update `{name}`: "
                     f"{result.user_message or 'write failed'}.")
    old = _in_transaction_prior(result, spec, old)
    await _refresh_settings_page(req)
    return Reply(SUCCESS,
                 f"✅ Updated `{name}` = `{value!r}` (was `{old!r}`).")


# --- registration — MODULE IMPORT (BUG A rule) --------------------------------------

_HANDLERS = (
    ("cleanup.settings_edit_route", settings_edit_route),
    ("cleanup.settings_reset_route", settings_reset_route),
    ("cleanup.settings_preset_pick", settings_preset_pick),
    ("cleanup.settings_number_submit", settings_number_submit),
)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


_register()


def ensure_widget_refs() -> None:
    _register()

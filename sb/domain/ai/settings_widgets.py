"""The ai settings edit/reset MUTATION widgets (band 7, settings-mutation
slice) — the shipped SubsystemSettingsView S6/S7 flow for the ai schema
(views/settings/subsystem_view.py `dispatch_edit_setting` +
edit_boolean/edit_enum/edit_number_presets/reset_button @7f7628e1), ported
onto the K7 `settings.set_scalar` op (the ONE audited write path to the
`settings` table — DB write + audit in one transaction, advisory
``settings.changed`` after commit; sb/domain/settings/ops.py).

Shipped dispatch rules, verbatim (`input_hint` first, then
value_type/allowed_values):

* bool                       → single-click toggle (read current, write the
                               inverse) — ``✅ Toggled `ai.<name>` → …``
* numeric_presets + presets  → the NumericPresetsView page (one button per
                               preset, current highlighted primary) —
                               ``✅ Updated … (was …)``
* str + allowed_values       → the enum select page — ``✅ Updated …``
* free-form str              → the text widget page whose Edit… button
                               ISSUES the shipped TextSettingModal twin
                               (G-10, the modal-arming slice); the submit
                               re-enters through the frozen modal adapter
                               — ``✅ Updated `ai.<name>` = …``
* Override… (presets page)   → the shipped NumberSettingModal twin, same
                               G-10 round-trip — ``✅ Updated … (was …)``
* reset (any scalar)         → write the declared default —
                               ``✅ Reset `ai.<name>` to default = …``

The widget pages are session-lifecycle panels of the ONE anchor (the AI
nav doctrine): opening one swaps the settings page in place and the
``↩ Back to Settings`` route rebuilds it fresh — the shipped ephemeral
follow-up + best-effort parent edit collapses into open→write→Back (click
routes are golden-unpinned; #151's ledgered class). After a toggle/reset
(clicks ON the settings page itself) the page embed refreshes in place
best-effort, the shipped `_refresh_parent` posture.

Registered at MODULE IMPORT (the BUG A rule) — the ensure-only burn-down
list stays untouched.
"""

from __future__ import annotations

import dataclasses
import logging

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.spec.outcomes import SUCCESS

logger = logging.getLogger("sb.domain.ai.settings_widgets")

__all__ = ["ensure_widget_refs", "spec_for_key", "widget_kind"]

_SUBSYSTEM = "ai"

#: shipped guard bytes (edit_boolean / reset_button / the widget write path).
_NEEDS_GUILD_TOGGLE = "❌ Toggle requires a guild context."
_NEEDS_GUILD_RESET = "❌ Reset requires a guild context."
_NEEDS_GUILD_EDIT = "❌ Edit requires a guild context."


def spec_for_key(key: str):
    """The shipped-page SettingSpec for one settings_key (the select option
    values are the shipped ``spec.name`` strings = our settings_key)."""
    from sb.domain.ai.settings_schema import SHIPPED_SCHEMA_SETTINGS

    for spec in SHIPPED_SCHEMA_SETTINGS:
        if spec.settings_key == key:
            return spec
    return None


def widget_kind(spec) -> str:
    """The shipped dispatch_edit_setting routing, verbatim order:
    input_hint first, then bool / str+allowed_values / int / free-text."""
    hint = (spec.input_hint or "").strip().lower()
    if hint == "numeric_presets" and spec.presets:
        return "presets"
    if str(spec.value_type) == "bool":
        return "toggle"
    if str(spec.value_type) == "str" and spec.allowed_values:
        return "enum"
    return "text"       # free-form str + the shipped int-modal fallback


def _typed_default(spec):
    return spec.default


async def _current_value(guild_id: int, spec):
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


def _serialize(spec, value) -> str:
    """The shipped `_serialise` legacy-KV string form (the read-path
    inverse: booleans as the exact "true"/"false" spellings)."""
    if str(spec.value_type) == "bool":
        return "true" if value else "false"
    return str(value)


async def _write_setting(req, spec, value):
    """One audited write through the K7 `settings.set_scalar` op (the
    shipped SettingsMutationPipeline lane: coerce/validate here, DB write +
    audit in ONE transaction inside the engine, `settings.changed` emitted
    AFTER commit)."""
    from sb.kernel import settings as ksettings
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    key = ksettings.persisted_key(_SUBSYSTEM, spec.name)
    return await engine.run(
        WorkflowRef("settings.set_scalar"),
        ctx_from_request(req, {
            "key": key,
            "value": _serialize(spec, value),
            "subsystem": _SUBSYSTEM,
            "name": spec.name,
        }))


async def _refresh_settings_page(req) -> None:
    """Best-effort in-place refresh of the settings page embed after a
    write landed from ITS OWN select row (the shipped `_refresh_parent`
    soft-fail posture: any miss is a debug log, never an error)."""
    try:
        from sb.kernel.panels.engine import refresh_session_view

        message = getattr(req.origin, "message", None)
        message_key = str(getattr(message, "id", "") or "")
        if not message_key:
            return
        await refresh_session_view(req, message_key=message_key,
                                   params=dict(req.args or {}))
    except Exception:  # noqa: BLE001 — the confirmation already rendered
        logger.debug("ai settings page refresh failed", exc_info=True)


async def _open_widget(req, panel_id: str, key: str) -> None:
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    args = {**dict(req.args or {}), "setting": key}
    await open_panel(PanelRef(panel_id), dataclasses.replace(req, args=args))


def _picked(req) -> str:
    values = tuple(req.args.get("values", ()) or ())
    return str(values[0]) if values else ""


# --- the settings-page select rows -------------------------------------------------


async def settings_edit_route(req) -> Reply | None:
    """The "Edit a setting…" pick — the shipped dispatch_edit_setting."""
    key = _picked(req)
    spec = spec_for_key(key)
    if spec is None:
        # shipped: f"❌ Unknown setting `{subsystem}.{name}`." (ephemeral)
        return Reply(SUCCESS, f"❌ Unknown setting `ai.{key}`.")
    kind = widget_kind(spec)
    if kind == "toggle":
        if not req.guild_id:
            return Reply(SUCCESS, _NEEDS_GUILD_TOGGLE)
        current = await _current_value(int(req.guild_id), spec)
        new_value = not bool(current)
        result = await _write_setting(req, spec, new_value)
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         f"❌ Couldn't update `ai.{key}`: "
                         f"{result.user_message or 'write failed'}.")
        await _refresh_settings_page(req)
        return Reply(SUCCESS, f"✅ Toggled `ai.{key}` → `{new_value!r}`.")
    if kind == "presets":
        await _open_widget(req, "ai.settings_edit_presets", key)
        return None
    if kind == "enum":
        await _open_widget(req, "ai.settings_edit_enum", key)
        return None
    # free-form text — the text widget page (its Edit… button issues the
    # shipped TextSettingModal twin; the shipped pick answered the select
    # interaction with the modal DIRECTLY, but a selector pick is
    # AUTO-deferred on this engine so a button intermediates — the D-0054
    # confirm-surface posture, ledgered).
    await _open_widget(req, "ai.settings_edit_text", key)
    return None


async def settings_reset_route(req) -> Reply:
    """The "Reset a setting…" pick — the shipped reset_button.reset_setting
    (functionally set_value(spec.default), recorded as a deliberate
    operator action through the same audited lane)."""
    key = _picked(req)
    spec = spec_for_key(key)
    if spec is None:
        return Reply(SUCCESS, f"❌ Unknown setting `ai.{key}`.")
    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_RESET)
    default = _typed_default(spec)
    result = await _write_setting(req, spec, default)
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     f"❌ Couldn't reset `ai.{key}`: "
                     f"{result.user_message or 'write failed'}.")
    await _refresh_settings_page(req)
    return Reply(SUCCESS,
                 f"✅ Reset `ai.{key}` to default = `{default!r}`.")


# --- the widget pages ---------------------------------------------------------------


async def settings_enum_pick(req) -> Reply:
    """The enum widget's select pick (shipped edit_enum._on_select) —
    write the picked allowed value."""
    key = str(req.args.get("setting") or "")
    spec = spec_for_key(key)
    if spec is None:
        return Reply(SUCCESS, f"❌ Unknown setting `ai.{key}`.")
    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_EDIT)
    picked = _picked(req)
    if picked not in tuple(str(v) for v in spec.allowed_values):
        return Reply(SUCCESS, f"❌ Unknown setting `ai.{key}`.")
    result = await _write_setting(req, spec, picked)
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     f"❌ Couldn't update `ai.{key}`: "
                     f"{result.user_message or 'write failed'}.")
    return Reply(SUCCESS, f"✅ Updated `ai.{key}` = `{picked!r}`.")


async def settings_preset_pick(req) -> Reply:
    """One preset button on the numeric-presets widget (shipped
    edit_number_presets._write_preset_value) — the slot index maps into
    the spec's declared preset roster."""
    key = str(req.args.get("setting") or "")
    spec = spec_for_key(key)
    if spec is None or not spec.presets:
        return Reply(SUCCESS, f"❌ Unknown setting `ai.{key}`.")
    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_EDIT)
    action = str(req.args.get("session_action") or "")
    if not action.startswith("preset_"):
        return Reply(SUCCESS, f"❌ Unknown setting `ai.{key}`.")
    try:
        index = int(action.rsplit("_", 1)[1])
        value = tuple(spec.presets)[index]
    except (ValueError, IndexError):
        return Reply(SUCCESS, f"❌ Unknown setting `ai.{key}`.")
    # pre-write read covers the NO-ROW display (the global/default
    # resolution chain — the shipped resolution.value posture)…
    old = await _current_value(int(req.guild_id), spec)
    result = await _write_setting(req, spec, value)
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     f"❌ Couldn't update `ai.{key}`: "
                     f"{result.user_message or 'write failed'}.")
    old = _in_transaction_prior(result, spec, old)
    return Reply(SUCCESS,
                 f"✅ Updated `ai.{key}` = `{value!r}` (was `{old!r}`).")


def _in_transaction_prior(result, spec, fallback):
    """When a per-guild row EXISTED, prefer the IN-TRANSACTION prior the
    write leg returned (LegOutcome.before over the upsert's
    SELECT-then-UPDATE) — a concurrent writer between the pre-write read
    and the commit can no longer misreport the "(was …)" byte (the #160
    codex-P3 posture, shared by every free-form/preset write)."""
    prior_raw = ((result.before or {}).get("write_scalar") or {}).get("value")
    if prior_raw is None:
        return fallback
    from sb.domain.settings.service import coerce_value

    coerced, ok, _diag = coerce_value(spec, str(prior_raw))
    return coerced if ok else spec.default


# --- the G-10 form submits (the modal-arming slice) ---------------------------------


async def settings_number_submit(req) -> Reply:
    """The Override… form's SUBMIT (shipped NumberSettingModal.on_submit):
    strip → coerce/validate against the picked SettingSpec (bounds +
    allowed_values ride the same coercer the read path uses) → the audited
    write — ``✅ Updated `ai.<key>` = `<new>` (was `<old>`).``. The
    `setting` param arrives through the kernel modal-args stash (the
    opening click's session args); a stash miss falls to the unknown-
    setting guard."""
    key = str(req.args.get("setting") or "")
    spec = spec_for_key(key)
    if spec is None:
        return Reply(SUCCESS, f"❌ Unknown setting `ai.{key}`.")
    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_EDIT)
    raw = str(req.args.get("new_value") or "").strip()
    from sb.domain.settings.service import coerce_value

    value, ok, diags = coerce_value(spec, raw)
    if not ok:
        # the shipped pipeline raised SettingsCoercionError("cannot coerce
        # value=<raw> to <type>: …") — the K7 envelope form carries the
        # same sentence body (#160's ledgered write-failure class).
        return Reply(SUCCESS,
                     f"❌ Couldn't update `ai.{key}`: cannot coerce "
                     f"value={raw!r} to {spec.value_type} "
                     f"({'; '.join(diags) or 'invalid value'}).")
    old = await _current_value(int(req.guild_id), spec)
    result = await _write_setting(req, spec, value)
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     f"❌ Couldn't update `ai.{key}`: "
                     f"{result.user_message or 'write failed'}.")
    old = _in_transaction_prior(result, spec, old)
    await _refresh_settings_page(req)
    return Reply(SUCCESS,
                 f"✅ Updated `ai.{key}` = `{value!r}` (was `{old!r}`).")


async def settings_text_submit(req) -> Reply:
    """The Edit… form's SUBMIT (shipped TextSettingModal.on_submit): the
    raw string writes VERBATIM (str settings — an empty submit writes the
    empty string, the shipped "empty = routing default" contract) —
    ``✅ Updated `ai.<key>` = `<new>`.`` (the shipped text ack carries no
    "(was …)")."""
    key = str(req.args.get("setting") or "")
    spec = spec_for_key(key)
    if spec is None:
        return Reply(SUCCESS, f"❌ Unknown setting `ai.{key}`.")
    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_EDIT)
    raw = req.args.get("new_value")
    value = "" if raw is None else str(raw)
    result = await _write_setting(req, spec, value)
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     f"❌ Couldn't update `ai.{key}`: "
                     f"{result.user_message or 'write failed'}.")
    await _refresh_settings_page(req)
    return Reply(SUCCESS, f"✅ Updated `ai.{key}` = `{value!r}`.")


# --- the chooser scope pickers (the NEXT slices' pending terminals) -----------------

_SCOPE_COPY = {
    # the policy chooser's five scope pickers are LIVE (the
    # policy-mutation slice — sb/domain/ai/policy_widgets.py).
    # behavior chooser (views/ai/behavior/* — the preset catalog +
    # instruction-profile binding are their own slice).
    "behavior_channel": ("The per-channel behavior preset picker ports "
                         "with the behavior-preset slice."),
    "behavior_category": ("The per-category behavior preset picker ports "
                          "with the behavior-preset slice."),
    "behavior_preview": ("The dry-run preview picker ports with the "
                         "behavior-preset slice — the Policy chooser's "
                         "Effective policy picker answers the dual "
                         "dry-run trace meanwhile."),
    "behavior_matrix": ("The routing-matrix picker ports with the "
                        "behavior-preset slice — `!ai routing` lists the "
                        "task table meanwhile."),
    # tools chooser (views/ai/tools/*).
    "tools_guild": ("The guild-default orchestration profile picker ports "
                    "with the orchestration-mutation slice."),
    "tools_channel": ("The per-channel orchestration profile picker ports "
                      "with the orchestration-mutation slice."),
    "tools_category": ("The per-category orchestration profile picker "
                       "ports with the orchestration-mutation slice."),
    "tools_preview": ("The dry-run orchestration preview ports with the "
                      "orchestration-mutation slice."),
}


async def chooser_scope_pending(req) -> Reply:
    """One honest pending terminal for every chooser scope button — the
    scope pages are the policy/orchestration-mutation slices' ports
    (`session_action` carries the clicked button's action_id)."""
    action = str(req.args.get("session_action") or "")
    return Reply(SUCCESS, _SCOPE_COPY.get(
        action, "This page ports with its mutation slice."))


# --- registration — MODULE IMPORT (BUG A rule) --------------------------------------

_HANDLERS = (
    ("ai.settings_edit_route", settings_edit_route),
    ("ai.settings_reset_route", settings_reset_route),
    ("ai.settings_enum_pick", settings_enum_pick),
    ("ai.settings_preset_pick", settings_preset_pick),
    ("ai.settings_number_submit", settings_number_submit),
    ("ai.settings_text_submit", settings_text_submit),
    ("ai.chooser_scope_pending", chooser_scope_pending),
)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


_register()


def ensure_widget_refs() -> None:
    _register()

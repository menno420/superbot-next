"""The ai BEHAVIOR PRESET PICKERS (band 7, the behavior-preset slice —
D-0071) — the shipped views/ai/behavior/{scope_picker,preset_picker}.py
flows on this engine:

* channel / category — the shipped two-step pick → preset list
  (``_BehaviorChannelSelect`` / ``_BehaviorCategorySelect``): the scope
  pick swaps the anchor to the PRESET PICKER page carrying the picked
  target + the shipped ``scope_label`` copy shape (``channel <#id>`` /
  ``category **name**``);
* preset pick — the shipped ``_PresetSelect.callback``: unknown-key
  refusal byte (``❌ Unknown preset `key`.``), then ONE audited scoped
  op through :func:`sb.domain.ai.behavior_presets.apply_preset` (the
  policy chokepoint — mode = the preset's recommended mode,
  instruction_profile_id = the preset row, min_level/cooldown
  PRESERVED), then the shipped confirmation ack verbatim
  (``✅ Bound preset `key` (mode `mode`) to scope **label**.
  mutation_id=`…`.``). Typed service refusals echo the shipped
  ``❌ {type(exc).__name__}: {exc}`` shape; an op-level write failure
  renders the #160-ledgered K7 envelope copy (never a shipped exception
  echo — D-0070(d)).

The rosters ride the same installable guild-scope port as the policy
pickers (sb/domain/ai/policy_widgets.py — uninstalled degrades to
empty_state, never a crash). Registered at MODULE IMPORT (BUG A rule)."""

from __future__ import annotations

import dataclasses
import logging

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import SUCCESS

logger = logging.getLogger("sb.domain.ai.behavior_widgets")

__all__ = [
    "behavior_category_pick",
    "behavior_channel_pick",
    "behavior_preset_options",
    "behavior_preset_pick",
    "ensure_behavior_widget_refs",
]

#: the policy-widget guard byte family (shipped chooser guard class).
_NEEDS_GUILD_EDIT = "❌ Edit requires a guild context."


def _picked(req) -> str:
    values = tuple(req.args.get("values", ()) or ())
    return str(values[0]) if values else ""


async def _open_page(req, panel_id: str, extra: dict) -> None:
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    args = {**dict(req.args or {}), **extra}
    await open_panel(PanelRef(panel_id), dataclasses.replace(req, args=args))


# --- the scope picks (select → preset picker page) -----------------------------------


async def behavior_channel_pick(req) -> None:
    """_BehaviorChannelSelect.callback — hand the picked channel to the
    preset picker (scope_label = the shipped ``channel {mention}``)."""
    target = _picked(req)
    await _open_page(req, "ai.behavior_preset_picker", {
        "behavior_scope": "channel", "behavior_target": target,
        "behavior_target_label": f"<#{target}>",
        "behavior_scope_label": f"channel <#{target}>"})
    return None


async def behavior_category_pick(req) -> None:
    """_BehaviorCategorySelect.callback — the shipped
    ``category **{label}**`` scope label (roster name, raw id
    fallback)."""
    from sb.domain.ai import policy_widgets

    target = _picked(req)
    label = await policy_widgets._label_for(
        int(req.guild_id or 0), "category", int(target or 0))
    await _open_page(req, "ai.behavior_preset_picker", {
        "behavior_scope": "category", "behavior_target": target,
        "behavior_target_label": label,
        "behavior_scope_label": f"category **{label}**"})
    return None


# --- the preset pick (select → the audited apply + confirmation) ---------------------


async def behavior_preset_pick(req) -> Reply:
    """_PresetSelect.callback, shipped order: guild guard → key lookup
    (the ``❌ Unknown preset`` byte) → apply through the policy
    chokepoint → the shipped confirmation ack."""
    from sb.domain.ai import behavior_presets as presets

    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_EDIT)
    scope = str(req.args.get("behavior_scope") or "")
    target = str(req.args.get("behavior_target") or "")
    if not target.isdigit():
        # a stale/foreign page open leaves the args bare — the guard
        # answers, never a write (the policy_mode_submit posture).
        return Reply(SUCCESS, _NEEDS_GUILD_EDIT)
    chosen_key = _picked(req)
    lookup = {p.key: p.preset_id
              for p in await presets.list_behavior_presets()}
    preset_id = lookup.get(chosen_key)
    if preset_id is None:
        # the shipped unknown-preset refusal byte, verbatim.
        return Reply(SUCCESS, f"❌ Unknown preset `{chosen_key}`.")
    try:
        applied = await presets.apply_preset(
            req, scope=scope, target_id=int(target), preset_id=preset_id)
    except presets.BehaviorPresetError as exc:
        # the shipped typed-error echo, verbatim.
        return Reply(SUCCESS, f"❌ {type(exc).__name__}: {exc}")
    result = applied.result
    if getattr(result, "outcome", None) != SUCCESS:
        # op-level failure — the #160-ledgered K7 envelope copy class
        # (never the shipped exception echo, D-0070(d)).
        label = str(req.args.get("behavior_target_label") or target)
        subject = (f"category **{label}**" if scope == "category"
                   else label)
        return Reply(getattr(result, "outcome", SUCCESS),
                     f"❌ Couldn't update AI policy for {subject}: "
                     f"{getattr(result, 'user_message', None) or 'write failed'}.")
    label = str(req.args.get("behavior_target_label") or target)
    return Reply(SUCCESS,
                 f"✅ Bound preset `{applied.preset_key}` "
                 f"(mode `{applied.recommended_mode}`) to "
                 f"{scope} **{label}**. "
                 f"mutation_id=`{applied.policy_mutation_id}`.")


# --- the preset option roster ----------------------------------------------------------


async def behavior_preset_options(ctx):
    """The shipped _PresetSelect options: label = the preset key,
    description = its headline (both catalog-fed; ≤25 by construction —
    seven seeds; a longer future catalog truncates like the shipped
    _MAX_OPTIONS cap)."""
    from sb.domain.ai import behavior_presets as presets

    try:
        rows = await presets.list_behavior_presets()
    except Exception:  # noqa: BLE001 — DB-free replay degrades to empty_state
        logger.debug("behavior preset roster read failed", exc_info=True)
        return ()
    return tuple({"label": p.key[:100], "value": p.key,
                  "description": p.headline[:100]}
                 for p in rows[:25])


# --- registration — MODULE IMPORT (BUG A rule) ------------------------------------------

_HANDLERS = (
    ("ai.behavior_channel_pick", behavior_channel_pick),
    ("ai.behavior_category_pick", behavior_category_pick),
    ("ai.behavior_preset_pick", behavior_preset_pick),
)

_PROVIDERS = (
    ("ai.behavior_preset_options", behavior_preset_options),
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


def ensure_behavior_widget_refs() -> None:
    _register()

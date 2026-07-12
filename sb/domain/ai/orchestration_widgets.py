"""The ai TOOLS PROFILE PICKERS (band 7, the orchestration-mutation
slice — the D-0070 parked ``views/ai/tools/{scope_view,preview_view}.py``
flows on this engine; oracle fragments reconstructed via search_code —
full-file oracle reads stay denied):

* guild — the shipped ``GuildToolsProfileView``: the "Tools · guild
  default" page IS the profile select (no target pick; NO clear option —
  the shipped ``_profile_options(include_clear=scope != "guild")``).
* channel / category — the shipped two-step pick → profile choice
  (``ChannelToolsSelectView`` / ``CategoryToolsSelectView`` →
  ``_ProfileChoiceView``): the scope pick swaps the anchor to the
  PROFILE PICKER page carrying the picked target (the shipped prompt
  byte "Pick an orchestration profile for {label}." — both shipped
  selects were native ChannelSelects whose labels render ``<#id>``;
  the category roster rides the D-0070(a) string-select lane).
* profile pick — the shipped ``_ProfileSelect.callback``: ``Clear
  (inherit)`` maps to ``profile_key=None``; the widget pre-checks the
  registered-profile roster and echoes the shipped
  ``❌ {type(exc).__name__}: {exc}`` shape for an unknown key, then ONE
  audited op (``ai.set_guild_orchestration`` /
  ``ai.set_channel_orchestration`` / ``ai.set_category_orchestration``)
  and the shipped ack verbatim: ``✅ {verb} (generation {N}).`` with
  verb = ``Set **{key}** as the orchestration profile for {label}`` /
  ``Cleared the orchestration profile for {label}``. An op-level write
  failure renders the #160-ledgered K7 envelope copy (never a shipped
  exception echo — D-0070(d)).
* preview — the shipped ``preview_view.py`` dry-run analyzer: kernel
  ``resolve_orchestration(dry_run=True)`` + ``select_tools`` at FULL
  (SYSTEM) scope over the registered tool specs ("so it isolates the
  *profile's* effect"), rendered as the shipped
  "AI Tools & Workflows — preview" embed (Resolved profile / Offered
  tools / Withheld by profile / Precedence + the dry_run footer).

Registered at MODULE IMPORT (BUG A rule)."""

from __future__ import annotations

import dataclasses
import logging
import uuid

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.spec.outcomes import SUCCESS

logger = logging.getLogger("sb.domain.ai.orchestration_widgets")

__all__ = [
    "build_orchestration_preview_embed",
    "ensure_orchestration_widget_refs",
    "orchestration_profile_options",
    "orchestration_profile_options_clear",
    "tools_category_pick",
    "tools_channel_pick",
    "tools_preview_pick",
    "tools_profile_pick",
]

#: the shipped scope_view sentinel — "remove the override at this scope"
#: (inherit the next layer). Distinct from any preset key.
_CLEAR_VALUE = "__inherit__"

#: the policy-widget guard byte family (shipped chooser guard class).
_NEEDS_GUILD_EDIT = "❌ Edit requires a guild context."
_NEEDS_GUILD_PREVIEW = "❌ Preview requires a guild context."


def _picked(req) -> str:
    values = tuple(req.args.get("values", ()) or ())
    return str(values[0]) if values else ""


async def _open_page(req, panel_id: str, extra: dict) -> None:
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    args = {**dict(req.args or {}), **extra}
    await open_panel(PanelRef(panel_id), dataclasses.replace(req, args=args))


# --- the profile option roster (the shipped _profile_options) -------------------------


def _profiles_shipped_order():
    """The shipped ``all_presets()`` order: the compatible default FIRST,
    then the rest (the kernel registry's sorted-by-key view happens to
    match the shipped insertion order for the five shipped presets)."""
    from sb.kernel.ai import orchestration

    profiles = list(orchestration.registered_profiles())
    default = [p for p in profiles
               if p.key == orchestration.DEFAULT_PROFILE_KEY]
    rest = [p for p in profiles
            if p.key != orchestration.DEFAULT_PROFILE_KEY]
    return (*default, *rest)


def _profile_option_rows(*, include_clear: bool):
    """The shipped SelectOption rows: label / value / truncated
    description per preset (+ the optional clear/inherit option). The
    25-option Discord cap truncates PRESETS, never the clear option
    (codex #187 P3: a 25th-slot clear must survive a grown registry —
    the shipped roster was 5, uncapped)."""
    profiles = _profiles_shipped_order()
    if include_clear:
        profiles = profiles[:24]
    options = [{"label": p.label[:100], "value": p.key,
                "description": p.description[:100]}
               for p in profiles[:25]]
    if include_clear:
        options.append({
            "label": "Clear (inherit)",
            "value": _CLEAR_VALUE,
            "description": "Remove this scope's profile; inherit the "
                           "next layer."})
    return tuple(options)


async def orchestration_profile_options(ctx):
    """The guild page's roster — presets only (the shipped
    ``include_clear=scope != "guild"``: the guild default has no clear)."""
    return _profile_option_rows(include_clear=False)


async def orchestration_profile_options_clear(ctx):
    """The channel/category profile page's roster — presets + the
    shipped Clear (inherit) option."""
    return _profile_option_rows(include_clear=True)


# --- the scope picks (select → profile picker page) -----------------------------------


async def tools_channel_pick(req) -> None:
    """ChannelToolsSelectView's pick — hand the picked channel to the
    profile picker (the shipped label byte ``<#id>``, the ChannelSelect
    mention)."""
    target = _picked(req)
    await _open_page(req, "ai.tools_profile_picker", {
        "tools_scope": "channel", "tools_target": target,
        "tools_target_label": f"<#{target}>"})
    return None


async def tools_category_pick(req) -> None:
    """CategoryToolsSelectView's pick — the shipped select was a native
    category-typed ChannelSelect whose label byte is the SAME ``<#id>``
    mention (scope_view callback: ``getattr(picked, "mention", None) or
    f"<#{picked.id}>"``); the roster string select is the D-0070(a)
    ledgered engine lane."""
    target = _picked(req)
    await _open_page(req, "ai.tools_profile_picker", {
        "tools_scope": "category", "tools_target": target,
        "tools_target_label": f"<#{target}>"})
    return None


# --- the profile pick (select → the audited write + confirmation) ---------------------


async def tools_profile_pick(req) -> Reply:
    """_ProfileSelect.callback, shipped order: guild guard → clear-value
    fold → the roster check (the shipped
    ``InvalidAIOrchestrationValueError`` echo; the leg RE-checks in-txn,
    §4.1) → the audited scoped op → the shipped
    ``✅ {verb} (generation {N}).`` ack."""
    from sb.domain.ai import orchestration_ops as ops
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_EDIT)
    scope = str(req.args.get("tools_scope") or "guild")
    target = str(req.args.get("tools_target") or "")
    if scope != "guild" and not target.isdigit():
        # a stale/foreign page open leaves the args bare — the guard
        # answers, never a write (the policy_mode_submit posture).
        return Reply(SUCCESS, _NEEDS_GUILD_EDIT)
    picked = _picked(req)
    profile_key = None if picked == _CLEAR_VALUE else picked
    if profile_key is not None:
        valid = sorted(ops.known_profile_keys())
        if profile_key not in valid:
            # the shipped view's typed-error echo, verbatim
            # (scope_view.py: f"❌ {type(exc).__name__}: {exc}" over the
            # seam's InvalidAIOrchestrationValueError sentence body —
            # rebuilt here because this engine's ValidatorError envelope
            # would prefix the sentence; the leg re-checks in-txn, §4.1).
            return Reply(SUCCESS,
                         "❌ InvalidAIOrchestrationValueError: unknown "
                         f"orchestration profile {profile_key!r}; "
                         f"must be one of {valid} (or null to clear)")

    if scope == "channel":
        op_key, params = "ai.set_channel_orchestration", {
            "channel_id": int(target)}
        label = str(req.args.get("tools_target_label") or f"<#{target}>")
    elif scope == "category":
        op_key, params = "ai.set_category_orchestration", {
            "category_id": int(target)}
        label = str(req.args.get("tools_target_label") or f"<#{target}>")
    else:
        op_key, params = "ai.set_guild_orchestration", {}
        label = str(req.args.get("tools_target_label") or "the guild")
    # the shipped mutation seam minted a uuid per write and carried it on
    # the advisory event (ai_orchestration_mutation mutation_id).
    result = await engine.run(WorkflowRef(op_key), ctx_from_request(req, {
        **params, "profile_key": profile_key,
        "mutation_id": uuid.uuid4().hex}))
    if result.outcome != SUCCESS:
        # op-level failure — the #160-ledgered K7 envelope copy class
        # (never the shipped exception echo, D-0070(d)).
        return Reply(result.outcome,
                     f"❌ Couldn't update the orchestration profile for "
                     f"{label}: {result.user_message or 'write failed'}.")
    after = (result.after or {}).get("orchestration_write") or {}
    try:
        generation = int(after.get("generation") or 0)
    except (TypeError, ValueError):
        generation = 0
    if profile_key is None:
        verb = f"Cleared the orchestration profile for {label}"
    else:
        verb = (f"Set **{profile_key}** as the orchestration profile for "
                f"{label}")
    return Reply(SUCCESS, f"✅ {verb} (generation {generation}).")


# --- the dry-run preview (the shipped preview_view.py analyzer) ------------------------


async def build_orchestration_preview_embed(*, guild_id: int,
                                            channel_id: int,
                                            category_id: int | None):
    """The shipped ``AI Tools & Workflows — preview`` embed: kernel
    dry-run resolution + deterministic selection at FULL (SYSTEM) scope
    ("so it isolates the *profile's* effect") — every byte the shipped
    builder set, on the kernel's own primitives."""
    from sb.kernel.ai import orchestration, tools_catalogue
    from sb.kernel.ai.contracts import AIScope
    from sb.kernel.panels.render import RenderedEmbed

    decision = await orchestration.resolve_orchestration(
        orchestration.OrchestrationContext(
            guild_id=int(guild_id), channel_id=int(channel_id),
            category_id=category_id),
        dry_run=True)
    candidates = tuple(t.spec for t in tools_catalogue.registered_tools())
    decisions = tools_catalogue.select_tools(
        candidates, scope=AIScope.SYSTEM,
        enabled_toolsets=decision.enabled_toolsets,
        disabled_tools=decision.disabled_tools)
    offered = [d.name for d in decisions if d.included]
    withheld = [(d.name, d.reason) for d in decisions if not d.included]

    toolsets = ("all" if decision.enabled_toolsets is None
                else (", ".join(decision.enabled_toolsets) or "none"))
    budget = decision.tool_budget
    group = getattr(decision.tool_choice, "group_name", None)
    resolved = (
        f"profile `{decision.profile_key}` (source `{decision.source}`)\n"
        f"toolsets: {toolsets}\n"
        f"tool choice: `{decision.tool_choice.mode.value}`"
        + (f" · group `{group}`" if group else "")
        + f"\nbudget: hops=`{budget.max_hops}` "
        f"calls=`{budget.max_calls if budget.max_calls is not None else '∞'}` "
        f"workflow=`{decision.workflow}`")
    fields = [("Resolved profile", resolved, False)]
    offered_text = (", ".join(f"`{n}`" for n in offered)
                    if offered else "_(none)_")
    fields.append((f"Offered tools ({len(offered)})",
                   offered_text[:1024], False))
    if withheld:
        lines = [f"`{name}` — {reason.value if reason else 'withheld'}"
                 for name, reason in withheld]
        fields.append((f"Withheld by profile ({len(withheld)})",
                       "\n".join(lines)[:1024], False))
    if decision.source_trace:
        trace = "\n".join(f"· {step}" for step in decision.source_trace)
        fields.append(("Precedence", trace[:1024], False))

    # the shipped best-effort guild-default footer decoration (the
    # AIConfigSnapshot.orchestration.guild_profile_key read — the SAME
    # single source the resolver consumed, so the display mirrors the
    # K10 reader here too; fail-safe None drops the decoration).
    from sb.domain.ai import readers

    guild_default = await readers.guild_orchestration_default(int(guild_id))
    footer = "dry_run=True · administrator-only · tools shown at full scope"
    if guild_default:
        footer += f" · guild default: {guild_default}"
    footer += " (per-caller scope narrows further)"

    return RenderedEmbed(
        title="AI Tools & Workflows — preview",
        description=(f"Resolving orchestration for <#{int(channel_id)}>.\n"
                     "_Dry-run only — no provider call, no state touched._"),
        fields=tuple(fields), footer=footer, style_token="blurple")


async def tools_preview_pick(req) -> Reply | None:
    """The shipped preview pick — the dry-run analyzer embed for the
    PICKED channel (its category resolves through the roster port, the
    policy preview posture)."""
    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_PREVIEW)
    from sb.domain.ai import policy_widgets

    target = int(_picked(req) or 0)
    roster = await policy_widgets._roster(int(req.guild_id))
    category_id = next((cat for cid, _name, cat in roster.text_channels
                        if int(cid) == target), None)
    embed = await build_orchestration_preview_embed(
        guild_id=int(req.guild_id), channel_id=target,
        category_id=category_id)
    from sb.domain.ai.service import card_panel_id

    # the preview pick is COMPONENT ingress -> the card carries the
    # family "AI home" back-route (VERDICT 009 AIP-02 consumption).
    await _open_page(req, card_panel_id(req), {"_card": embed})
    return None


# --- registration — MODULE IMPORT (BUG A rule) ------------------------------------------

_HANDLERS = (
    ("ai.tools_channel_pick", tools_channel_pick),
    ("ai.tools_category_pick", tools_category_pick),
    ("ai.tools_profile_pick", tools_profile_pick),
    ("ai.tools_preview_pick", tools_preview_pick),
)

_PROVIDERS = (
    ("ai.orchestration_profile_options", orchestration_profile_options),
    ("ai.orchestration_profile_options_clear",
     orchestration_profile_options_clear),
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


def ensure_orchestration_widget_refs() -> None:
    _register()

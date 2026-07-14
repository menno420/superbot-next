"""The 🧹 Cleanup Policies panel family — the oracle
``disbot/views/cleanup/policy_panel.py`` @9776401 (diagnostics view +
presets builder + custom builder + remove flow) as declared PanelSpecs
(the 2026-07-13 completeness-remainders residue: the ONE pending the
#408 slice deliberately left).

The oracle chained EPHEMERAL messages per step (BaseView + one select
each); this engine expresses the same flow as page swaps carrying the
staged state in session args (the ai policy/behavior/tools ledgered
posture) — same steps, same copy. Every sub-page carries the
↩ Back to Policies route (the never-strand posture the ai pickers set;
the oracle's ephemeral steps simply expired). The top view's three
buttons keep their shipped PERSISTENT ``cleanup_policy:*`` custom_ids
verbatim (``custom_id_override`` — the cleanup-hub precedent) and the
oracle attached ``↩ Back to Cleanup`` (cogs/cleanup/panel.py
``_attach_back_to_cleanup_button``) — the extra nav route here.

Native pick fidelity, ledgered: the channel pick rides the engine's
Discord-NATIVE channel select (wire type 8 — the D-0070 lane, the
shipped ``_ChannelPickSelect`` shape); the oracle's CATEGORY pick was a
category-typed native ChannelSelect, which this engine expresses as the
roster-fed string select (the D-0070(a) LEDGERED lane — the ai
category pickers' posture; the native picker is text-channel-typed).

``cl_pol_``-prefixed action/selector ids — K1 custom_id claims are
repo-global on the leaf id (the cl_refresh precedent);
``manifest_compile`` fences collisions.
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    NavRouteSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
    SelectorKind,
    SelectorSpec,
    TextBlock,
)
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    is_registered,
    panel,
    provider,
)

__all__ = [
    "cleanup_policies_category_pick_spec",
    "cleanup_policies_channel_pick_spec",
    "cleanup_policies_custom_spec",
    "cleanup_policies_level_spec",
    "cleanup_policies_preview_spec",
    "cleanup_policies_remove_spec",
    "cleanup_policies_scope_spec",
    "cleanup_policies_spec",
    "ensure_policy_panel_refs",
    "install_cleanup_policy_panels",
]

_MAX_LISTED_ROWS = 15  # oracle constant

#: the diagnostics description (oracle diagnostics_embed_from, verbatim).
_DIAG_DESCRIPTION = (
    "Resolution walks **channel → category → guild → default**; the most "
    "specific override wins. Threads inherit from their parent channel."
)

#: the oracle footers (dynamic on emptiness — the renderer override).
_DIAG_FOOTER = ("Read-only summary. Use the buttons below to set or remove "
                "policies.")
_DIAG_FOOTER_EMPTY = "Use “Set a policy” to add one."

#: the Command Access disambiguation tip (oracle _COMMAND_ACCESS_HINT).
_COMMAND_ACCESS_HINT = (
    "These levels only delete **invalid/blocked** command-style messages. "
    "To delete **any** command typed in a channel where commands aren't "
    "allowed, use **Command Access → 🗑️ Delete blocked commands** in "
    "`!settings`."
)

#: the preview footer byte (oracle preview_embed_from).
_PREVIEW_FOOTER = "Nothing has been written yet."

#: the oracle preview degrade byte (_LevelSelect / _CustomLevelView).
_PREVIEW_FAILED = "Could not build the preview — see logs."

#: the oracle scope options (_SCOPE_OPTIONS, verbatim).
_SCOPE_OPTIONS = (
    {"label": "Guild default", "value": "guild", "emoji": "🌐",
     "description": "Baseline level for every channel without an override."},
    {"label": "Category override", "value": "category", "emoji": "📁",
     "description": "Override one category (its channels inherit unless "
                    "overridden)."},
    {"label": "Channel override", "value": "channel", "emoji": "📡",
     "description": "Override one specific channel."},
)

#: every sub-page's back route (the never-strand posture; the oracle's
#: ephemeral steps expired instead).
_BACK_TO_POLICIES = NavigationSpec(
    show_help=False, show_home=False,
    extra_routes=(NavRouteSpec(label="↩ Back to Policies",
                               route=PanelRef("cleanup.policies")),))

#: the top view's back route — the oracle attached "↩ Back to Cleanup"
#: (cogs/cleanup/panel.py _attach_back_to_cleanup_button, label verbatim).
_BACK_TO_CLEANUP = NavigationSpec(
    show_help=False, show_home=False,
    extra_routes=(NavRouteSpec(label="↩ Back to Cleanup",
                               route=PanelRef("cleanup.hub")),))

_PAGE_JUSTIFICATION = (
    "the page's prompt/summary copy is parameterized on the PICKED flow "
    "state (scope label, staged column values) — per-open copy outside "
    "the static grammar (the ai.policy_scope_edit / ai."
    "settings_edit_presets precedent). The override delegates to the "
    "grammar renderer and supplies ONLY the dynamic description (+ the "
    "level page's oracle placeholder byte).")


# --- field providers ---------------------------------------------------------------


def _format_row(row) -> str:
    """One Overrides line (oracle _format_row, verbatim)."""
    flags = ""
    if row.is_ineffective:
        flags = " ⚠️ *legacy key — not applied; re-set to fix*"
    elif row.is_stale:
        flags = " ⚠️ *scope deleted*"
    return (f"• **{row.target_label}** → `{row.display_level}` "
            f"({row.delete_after_seconds}s){flags}")


async def _policies_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The diagnostics fields (oracle diagnostics_embed_from, verbatim
    bytes; a headless/db-free read renders the empty state)."""
    from sb.domain.cleanup import policy_service as svc

    try:
        diag = await svc.collect_cleanup_diagnostics(
            int(getattr(ctx, "guild_id", 0) or 0))
    except Exception:  # noqa: BLE001 — a headless/db-free read renders empty
        diag = None
    if diag is None or not diag.rows:
        return (("Configured policies",
                 "_None — every scope uses the fallback default (delete "
                 "after 5s)._"),
                ("ℹ️ Tip", _COMMAND_ACCESS_HINT))

    fields = []
    counts = ", ".join(f"{name}×{n}"
                       for name, n in sorted(diag.level_counts.items()))
    fields.append((f"Configured policies ({diag.total})", counts or "_none_"))
    listed = diag.rows[:_MAX_LISTED_ROWS]
    body = "\n".join(_format_row(r) for r in listed)
    if diag.total > _MAX_LISTED_ROWS:
        body += f"\n… and {diag.total - _MAX_LISTED_ROWS} more."
    fields.append(("Overrides", body))
    if diag.ineffective_rows:
        fields.append((
            "⚠️ Ineffective rows",
            f"{len(diag.ineffective_rows)} guild row(s) are stored under a "
            "legacy key the resolver never reads. **Fix:** press "
            "**🗑️ Remove a policy** to clear it, then **🔧 Set a policy** "
            "to re-set the guild default."))
    if diag.stale_rows:
        fields.append((
            "⚠️ Stale overrides",
            f"{len(diag.stale_rows)} override(s) target a channel/category "
            "that no longer exists. Use **🗑️ Remove a policy** to clear "
            "them."))
    fields.append(("ℹ️ Tip", _COMMAND_ACCESS_HINT))
    return tuple(fields)


# --- the top diagnostics panel --------------------------------------------------------


def cleanup_policies_spec() -> PanelSpec:
    """CleanupPolicyPanelView + diagnostics_embed_from: the read-only
    health report over the 🔧 Set / 🗑️ Remove / 🔄 Refresh trio (shipped
    persistent ``cleanup_policy:*`` custom_ids verbatim)."""
    return PanelSpec(
        panel_id="cleanup.policies",
        subsystem="cleanup",
        title="🧹 Cleanup Policies — Diagnostics",
        audience=Audience.INVOKER,
        # the shipped accent — ADMIN_COLOR == discord.Color.red().
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(TextBlock(_DIAG_DESCRIPTION),
              FieldsBlock(provider=ProviderRef("cleanup.policies_fields"))),
        actions=(
            PanelActionSpec(
                action_id="cl_pol_build", label="🔧 Set a policy",
                style=ActionStyle.SUCCESS, audience_tier="administrator",
                handler=PanelRef("cleanup.policies_scope"),
                custom_id_override="cleanup_policy:build"),
            PanelActionSpec(
                action_id="cl_pol_remove", label="🗑️ Remove a policy",
                style=ActionStyle.DANGER, audience_tier="administrator",
                handler=HandlerRef("cleanup.policies_remove_route"),
                custom_id_override="cleanup_policy:remove"),
            PanelActionSpec(
                action_id="cl_pol_refresh", label="🔄 Refresh",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=PanelRef("cleanup.policies"),
                result_render=ResultRender.REFRESH_PANEL,
                custom_id_override="cleanup_policy:refresh"),
        ),
        navigation=_BACK_TO_CLEANUP,
        session_lifecycle=True,
        renderer_override=HandlerRef("cleanup.render_policies"),
        justification=(
            "the shipped footer swaps on emptiness — 'Use “Set a policy” "
            "to add one.' with no stored rows, else 'Read-only summary. "
            "Use the buttons below to set or remove policies.' "
            "(views/cleanup/policy_panel.py diagnostics_embed_from) — "
            "dynamic copy outside FooterMode's none/subsystem/provenance "
            "vocabulary (the cleanup-hub footer precedent). The override "
            "delegates to the grammar renderer and replaces ONLY the "
            "footer; body, fields, actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("cl_pol_build", "cl_pol_remove", "cl_pol_refresh"),
        )),)),
    )


# --- the builder flow pages -------------------------------------------------------------


def cleanup_policies_scope_spec() -> PanelSpec:
    """_ScopeSelect — 'Choose what to set cleanup for:' (byte verbatim)
    over the three scope options."""
    return PanelSpec(
        panel_id="cleanup.policies_scope",
        subsystem="cleanup",
        title="🧹 Cleanup Policies — Set a policy",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(TextBlock("Choose what to set cleanup for:"),),
        selectors=(
            SelectorSpec(
                selector_id="cl_pol_scope", kind=SelectorKind.ENUM,
                options_source=_SCOPE_OPTIONS,
                placeholder="Pick a scope to set cleanup for…",
                audience_tier="administrator",
                on_select=HandlerRef("cleanup.policies_scope_pick")),
        ),
        navigation=_BACK_TO_POLICIES,
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(("cl_pol_scope",),)),)),
    )


def cleanup_policies_channel_pick_spec() -> PanelSpec:
    """_ChannelPickSelect — the Discord-NATIVE channel picker (the
    D-0070 lane; the shipped ChannelSelect shape)."""
    return PanelSpec(
        panel_id="cleanup.policies_channel_pick",
        subsystem="cleanup",
        title="🧹 Cleanup Policies — Set a policy",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(TextBlock("Pick a channel to override:"),),
        selectors=(
            SelectorSpec(
                selector_id="cl_pol_channel", kind=SelectorKind.CHANNEL,
                placeholder="Pick a channel…",
                audience_tier="administrator",
                on_select=HandlerRef("cleanup.policies_channel_pick")),
        ),
        navigation=_BACK_TO_POLICIES,
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(("cl_pol_channel",),)),)),
    )


def cleanup_policies_category_pick_spec() -> PanelSpec:
    """_CategoryPickSelect — the roster-fed category select (the
    D-0070(a) ledgered lane; the oracle's was a category-typed native
    ChannelSelect — module-doc ledger)."""
    return PanelSpec(
        panel_id="cleanup.policies_category_pick",
        subsystem="cleanup",
        title="🧹 Cleanup Policies — Set a policy",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(TextBlock("Pick a category to override:"),),
        selectors=(
            SelectorSpec(
                selector_id="cl_pol_category", kind=SelectorKind.ENTITY,
                options_source=ProviderRef(
                    "cleanup.policies_category_options"),
                placeholder="Pick a category…",
                audience_tier="administrator",
                on_select=HandlerRef("cleanup.policies_category_pick")),
        ),
        navigation=_BACK_TO_POLICIES,
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(("cl_pol_category",),)),)),
    )


def cleanup_policies_level_spec() -> PanelSpec:
    """_LevelSelect — the preset roster + ⚙️ Custom…; the prompt + the
    ``Level for {label}…`` placeholder carry the picked scope
    (renderer override)."""
    return PanelSpec(
        panel_id="cleanup.policies_level",
        subsystem="cleanup",
        title="🧹 Cleanup Policies — Set a policy",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="cl_pol_level", kind=SelectorKind.ENUM,
                options_source=ProviderRef("cleanup.policies_level_options"),
                placeholder="Pick a cleanup level…",
                audience_tier="administrator",
                on_select=HandlerRef("cleanup.policies_level_pick")),
        ),
        navigation=_BACK_TO_POLICIES,
        session_lifecycle=True,
        renderer_override=HandlerRef("cleanup.render_policies_level"),
        justification=_PAGE_JUSTIFICATION,
        layout=LayoutSpec(pages=(PageSpec(rows=(("cl_pol_level",),)),)),
    )


def cleanup_policies_custom_spec() -> PanelSpec:
    """_CustomLevelView — the select-driven custom builder (no typing):
    three pickers hold the staged choice in session args; changing a
    picker re-renders the page so each select reflects the current pick
    (the oracle rebuild posture); 🔎 Preview & apply routes the SAME
    explicit columns through the shared dry-run page."""
    return PanelSpec(
        panel_id="cleanup.policies_custom",
        subsystem="cleanup",
        title="🧹 Cleanup Policies — Custom level",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="cl_pol_custom_preview", label="🔎 Preview & apply",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("cleanup.policies_custom_preview")),
        ),
        selectors=(
            SelectorSpec(
                selector_id="cl_pol_after", kind=SelectorKind.ENUM,
                options_source=ProviderRef("cleanup.policies_after_options"),
                placeholder="Delete after…",
                audience_tier="administrator",
                on_select=HandlerRef("cleanup.policies_custom_after")),
            SelectorSpec(
                selector_id="cl_pol_invalid", kind=SelectorKind.ENUM,
                options_source=ProviderRef(
                    "cleanup.policies_invalid_options"),
                placeholder="Delete invalid commands?",
                audience_tier="administrator",
                on_select=HandlerRef("cleanup.policies_custom_invalid")),
            SelectorSpec(
                selector_id="cl_pol_failed", kind=SelectorKind.ENUM,
                options_source=ProviderRef("cleanup.policies_failed_options"),
                placeholder="Delete failed commands?",
                audience_tier="administrator",
                on_select=HandlerRef("cleanup.policies_custom_failed")),
        ),
        navigation=_BACK_TO_POLICIES,
        session_lifecycle=True,
        renderer_override=HandlerRef("cleanup.render_policies_custom"),
        justification=_PAGE_JUSTIFICATION,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("cl_pol_after",),
            ("cl_pol_invalid",),
            ("cl_pol_failed",),
            ("cl_pol_custom_preview",),
        )),)),
    )


def cleanup_policies_preview_spec() -> PanelSpec:
    """preview_embed_from + _ConfirmApplyView — the dry-run embed
    (recomputed at render over the REAL resolver, so preview == runtime)
    over ✅ Apply / ✖ Cancel."""
    return PanelSpec(
        panel_id="cleanup.policies_preview",
        subsystem="cleanup",
        title="🔎 Dry run — review before applying",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="orange",
                             footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="cl_pol_apply", label="✅ Apply",
                style=ActionStyle.SUCCESS, audience_tier="administrator",
                handler=HandlerRef("cleanup.policies_apply"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="cl_pol_cancel", label="✖ Cancel",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("cleanup.policies_cancel"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=_BACK_TO_POLICIES,
        session_lifecycle=True,
        renderer_override=HandlerRef("cleanup.render_policies_preview"),
        justification=(
            "the dry-run embed is fully runtime-parameterized: current-"
            "vs-after resolution over the real resolver, the orange/"
            "greyple will_change accent, the No-change field and the "
            "per-preview ⚠️ Note warnings (views/cleanup/policy_panel.py "
            "preview_embed_from) — outside the static grammar. The "
            "override delegates to the grammar renderer and supplies the "
            "description, fields, footer and style token."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("cl_pol_apply", "cl_pol_cancel"),
        )),)),
    )


def cleanup_policies_remove_spec() -> PanelSpec:
    """_RemoveSelect — one option per stored row (legacy/stale flagged),
    the oracle prompt byte as the body."""
    return PanelSpec(
        panel_id="cleanup.policies_remove",
        subsystem="cleanup",
        title="🧹 Cleanup Policies — Remove a policy",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(TextBlock("Pick the override to remove (it will fall back to "
                        "its parent scope):"),),
        selectors=(
            SelectorSpec(
                selector_id="cl_pol_remove_pick", kind=SelectorKind.ENTITY,
                options_source=ProviderRef("cleanup.policies_remove_options"),
                placeholder="Pick a policy to remove…",
                audience_tier="administrator",
                empty_state="There are no stored cleanup overrides to "
                            "remove.",
                on_select=HandlerRef("cleanup.policies_remove_pick")),
        ),
        navigation=_BACK_TO_POLICIES,
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(("cl_pol_remove_pick",),)),)),
    )


# --- renderer overrides ---------------------------------------------------------------


async def _render_policies(spec: PanelSpec, ctx) -> object:
    """Grammar render + the emptiness-swapped footer (see justification).
    Emptiness reads off the rendered fields — the Overrides field exists
    only when stored rows do."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    has_rows = any(f[0] == "Overrides" for f in rendered.embed.fields)
    footer = _DIAG_FOOTER if has_rows else _DIAG_FOOTER_EMPTY
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed, footer=footer))


async def _render_policies_level(spec: PanelSpec, ctx) -> object:
    """The level page's per-scope prompt + placeholder (oracle bytes:
    'Pick the guild-default cleanup level:' / 'Pick the cleanup level
    for category **{name}**:' / 'Pick the cleanup level for #{name}:'
    and the select's 'Level for {label}…')."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    params = ctx.params or {}
    scope = str(params.get("pol_scope") or "")
    label = str(params.get("pol_label") or "")
    if scope == "guild":
        description = "Pick the guild-default cleanup level:"
    elif scope == "category":
        bare = label[len("Category "):] if label.startswith("Category ") else label
        description = f"Pick the cleanup level for category **{bare}**:"
    else:
        description = f"Pick the cleanup level for {label}:"
    placeholder = f"Level for {label}…" if label else "Pick a cleanup level…"
    components = tuple(
        _dc_replace(comp, placeholder=placeholder, label=placeholder)
        if comp.custom_id.endswith(".cl_pol_level") else comp
        for comp in rendered.components)
    return _dc_replace(
        rendered, components=components,
        embed=_dc_replace(rendered.embed, description=description))


async def _render_policies_custom(spec: PanelSpec, ctx) -> object:
    """The custom builder's summary description (oracle
    _CustomLevelView.summary, bytes verbatim over the staged args)."""
    from sb.domain.cleanup.policy_widgets import DURATION_LABELS
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    params = ctx.params or {}
    try:
        after = int(str(params.get("pol_das") or "10"))
    except ValueError:
        after = 10
    invalid = str(params.get("pol_div") or "yes") == "yes"
    failed = str(params.get("pol_dfc") or "no") == "yes"
    description = (
        "**Custom cleanup policy** — pick values, then **Preview & apply**:\n"
        f"• Delete after: **{DURATION_LABELS.get(after, f'{after}s')}**\n"
        f"• Delete invalid commands: **{'Yes' if invalid else 'No'}**\n"
        f"• Delete failed commands: **{'Yes' if failed else 'No'}**")
    return _dc_replace(
        rendered, embed=_dc_replace(rendered.embed, description=description))


async def _render_policies_preview(spec: PanelSpec, ctx) -> object:
    """The dry-run embed (oracle preview_embed_from, bytes verbatim),
    recomputed at render over the REAL resolver; a failed preview
    renders the oracle degrade byte ('Could not build the preview — see
    logs.') instead of crashing the page."""
    from sb.domain.cleanup import policy_service as svc
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    params = ctx.params or {}
    scope = str(params.get("pol_scope") or "")
    target = str(params.get("pol_target") or "")
    div = str(params.get("pol_div") or "yes") == "yes"
    dfc = str(params.get("pol_dfc") or "no") == "yes"
    try:
        das = int(str(params.get("pol_das") or "10"))
    except ValueError:
        das = 10
    level_label = str(params.get("pol_level") or "") or None
    try:
        preview = await svc.preview_cleanup_columns(
            int(ctx.guild_id or 0), scope, int(target),
            delete_invalid_commands=div, delete_failed_commands=dfc,
            delete_after_seconds=das, level_label=level_label)
    except Exception:  # noqa: BLE001 — preview must never crash the flow
        import logging

        logging.getLogger("sb.domain.cleanup.policy_panels").exception(
            "cleanup preview failed")
        return _dc_replace(rendered, embed=_dc_replace(
            rendered.embed, description=_PREVIEW_FAILED))

    cur = preview.current
    fields = [
        ("Currently resolves to",
         f"delete={'yes' if cur.delete_message else 'no'}, "
         f"after={cur.delete_after_seconds}s\n"
         f"_source: {cur.resolved_from.value}_", True),
        ("After applying",
         f"invalid cmds={'yes' if preview.new_delete_message else 'no'}, "
         f"failed cmds="
         f"{'yes' if preview.new_delete_failed_commands else 'no'}, "
         f"after={preview.new_delete_after_seconds}s\n"
         f"_source: {preview.scope_type} override_", True),
    ]
    if not preview.will_change:
        fields.append(("No change",
                       "This scope already resolves exactly this way.",
                       False))
    for warning in preview.warnings:
        fields.append(("⚠️ Note", warning, False))
    embed = _dc_replace(
        rendered.embed,
        description=f"Set **{preview.target_label}** to `{preview.level}`?",
        fields=tuple(fields),
        footer=_PREVIEW_FOOTER,
        style_token="orange" if preview.will_change else "greyple")
    return _dc_replace(rendered, embed=embed)


# --- registration -----------------------------------------------------------------


_PANEL_SPECS = (
    ("cleanup.policies", cleanup_policies_spec),
    ("cleanup.policies_scope", cleanup_policies_scope_spec),
    ("cleanup.policies_channel_pick", cleanup_policies_channel_pick_spec),
    ("cleanup.policies_category_pick", cleanup_policies_category_pick_spec),
    ("cleanup.policies_level", cleanup_policies_level_spec),
    ("cleanup.policies_custom", cleanup_policies_custom_spec),
    ("cleanup.policies_preview", cleanup_policies_preview_spec),
    ("cleanup.policies_remove", cleanup_policies_remove_spec),
)

_RENDERERS = (
    ("cleanup.render_policies", _render_policies),
    ("cleanup.render_policies_level", _render_policies_level),
    ("cleanup.render_policies_custom", _render_policies_custom),
    ("cleanup.render_policies_preview", _render_policies_preview),
)


def _register_refs() -> None:
    from sb.spec.refs import handler

    for panel_id, factory in _PANEL_SPECS:
        if not is_registered(PanelRef(panel_id)):
            panel(panel_id)(factory)
    for name, fn in _RENDERERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)
    if not is_registered(ProviderRef("cleanup.policies_fields")):
        provider("cleanup.policies_fields")(_policies_fields)


_register_refs()


def install_cleanup_policy_panels() -> tuple[PanelSpec, ...]:
    """Register the panels with the panels registry (fences run here);
    composition-root/boot call. Idempotent for identical specs."""
    specs = tuple(factory() for _pid, factory in _PANEL_SPECS)
    for spec in specs:
        try:
            register_panel(spec)
        except ValueError as exc:
            if ("already registered" not in str(exc)
                    and "duplicate" not in str(exc)):
                raise
    return specs


def ensure_policy_panel_refs() -> None:
    """Idempotent re-arm of the panel/handler/provider refs."""
    _register_refs()

"""Game-sections SETTINGS surface (slice 2 of D-0082,
docs/design/game-sections.md §5) — enable a whole section OR pick a few
games, per guild.

The panel is registry-driven over ``sb.spec.sections`` (declared in
``sb/manifest/games.py`` — the SBW replacement slot, §7): per section one
**Enable all** button (writes ``enabled=None`` per game — the override is
DELETED back to registry default-enabled, design §5 verbatim) and one
multi-select whose options are the section's games with ``default`` =
currently enabled; the submit DIFFS the selection into per-game writes
(newly selected → ``enabled=None``, newly deselected → ``enabled=False``).

Every mutation goes through the existing governance K7 ``SET_VISIBILITY``
op via ``sb/domain/governance/service.py::set_subsystem_visibility`` (the
audited seam: K7 run + post-commit guild-cache invalidation) with the
actor's WorkflowContext — NO new store, NO migration (design §4). The
governance import is LAZY (call-time) — the established
domain→governance seam shape the slice-1 read seam already flagged
(PL-001, ``sb/domain/games/sections.py``). Reads use governance
``subsystem_enabled`` per game key DIRECTLY (not ``enabled_games``): the
settings surface must show DISABLED games too, and the read seam drops
fully-disabled sections (slice-1 card flag).

After a write the page re-renders best-effort in place via
``refresh_session_view`` (the armed ``sb/domain/ai/settings_widgets.py``
``_refresh_parent`` posture); any later fresh open re-resolves at click
time anyway (engine contract, design §6.1).

Layout budget (compile fences, ``sb/kernel/panels/compile.py``): one
select row per section + ONE shared enable-all button row + the nav row —
today's 2 sections = 4 rows / 5 components, headroom to 3 sections
(4 rows cap-side) before the roster needs paging.

Refs register at MODULE IMPORT (the composition-parity invariant) — but
the per-section refs depend on the sections registry, which the games
manifest populates BEFORE calling ``install_sections_panel()``; the
module-import pass arms whatever is registered at import time and the
install/ensure calls re-arm idempotently.
"""

from __future__ import annotations

import logging

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.kernel.panels.registry import register_panel
from sb.spec.outcomes import SUCCESS
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    SelectorKind,
    SelectorSpec,
    TextBlock,
)
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    handler,
    is_registered,
    panel,
    provider,
)
from sb.spec.sections import GameSectionSpec, all_sections, get_section

logger = logging.getLogger("sb.domain.games.sections_panel")

__all__ = [
    "SECTIONS_PANEL_ID",
    "ensure_sections_panel_refs",
    "games_sections_spec",
    "install_sections_panel",
]

SECTIONS_PANEL_ID = "games.sections"
_FIELDS_PROVIDER = "games.sections_fields"

_DESCRIPTION = (
    "Enable whole game sections or pick a few games for this server. "
    "**Enable all** clears every override in a section (back to "
    "default-enabled); the dropdowns show what is enabled right now — "
    "change the selection to toggle individual games. Disabled games "
    "drop off the Games hub and their commands are refused."
)

_NEEDS_GUILD = "❌ Game sections are configured per server — use this in a guild."


# --- reads (lazy domain→governance, the slice-1 seam shape) -------------------


async def _game_enabled(guild_id: int, key: str) -> bool:
    from sb.domain.governance import service as governance

    return await governance.subsystem_enabled(guild_id, key)


def _ensure_fields_provider() -> ProviderRef:
    ref = ProviderRef(_FIELDS_PROVIDER)
    if not is_registered(ref):
        @provider(_FIELDS_PROVIDER)
        async def sections_fields(ctx: object):
            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            fields = []
            for spec in all_sections():
                lines = []
                for entry in spec.games:
                    on = await _game_enabled(guild_id, entry.key)
                    lines.append(f"{'✅' if on else '🚫'} {entry.emoji} "
                                 f"**{entry.label}**")
                fields.append((f"{spec.emoji} {spec.title}",
                               "\n".join(lines)))
            if not fields:
                # honest empty state (owner-ordered render rule): the
                # registry is populated at manifest import — an empty
                # table means boot never registered the sections.
                return ((
                    "No game sections registered",
                    "The sections registry is empty — the games manifest "
                    "declares the DEFAULT inventory at boot "
                    "(docs/design/game-sections.md §3)."),)
            return tuple(fields)
    return ref


def _options_provider_name(section_key: str) -> str:
    return f"games.sections_options_{section_key}"


def _ensure_options_provider(section_key: str) -> ProviderRef:
    name = _options_provider_name(section_key)
    ref = ProviderRef(name)
    if not is_registered(ref):
        @provider(name)
        async def section_options(ctx: object, _key: str = section_key):
            spec = get_section(_key)
            if spec is None:
                return ()
            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            options = []
            for entry in spec.games:
                on = await _game_enabled(guild_id, entry.key)
                options.append({"value": entry.key, "label": entry.label,
                                "emoji": entry.emoji, "default": on})
            return tuple(options)
    return ref


# --- writes (the ONE audited seam — governance K7 SET_VISIBILITY) -------------


async def _set_visibility(req, subsystem: str, enabled: bool | None):
    """One K7-run write with the actor's WorkflowContext (design §5:
    the audited seam, never a direct store write)."""
    from sb.domain.governance import service as governance

    return await governance.set_subsystem_visibility(
        ctx_from_request(req, {}), scope_type="guild",
        scope_id=int(req.guild_id or 0), subsystem=subsystem,
        enabled=enabled)


async def _refresh_page(req) -> None:
    """Best-effort in-place refresh after a write landed (the armed
    ai/settings_widgets ``_refresh_parent`` posture: a miss is a debug
    log, never an error — the next fresh open re-resolves anyway)."""
    try:
        from sb.kernel.panels.engine import refresh_session_view

        message = getattr(req.origin, "message", None)
        message_key = str(getattr(message, "id", "") or "")
        if not message_key:
            return
        await refresh_session_view(req, message_key=message_key,
                                   params=dict(req.args or {}))
    except Exception:  # noqa: BLE001 — the confirmation already rendered
        logger.debug("game-sections page refresh failed", exc_info=True)


def _enable_all_handler(section_key: str):
    async def enable_all(req) -> Reply:
        """Enable a whole section: ``enabled=None`` per game — the
        override row is DELETED back to registry default-enabled
        (design §5 verbatim)."""
        spec = get_section(section_key)
        if spec is None:
            return Reply(SUCCESS, f"❌ Unknown game section `{section_key}`.")
        if not req.guild_id:
            return Reply(SUCCESS, _NEEDS_GUILD)
        done = 0
        for entry in spec.games:
            result = await _set_visibility(req, entry.key, None)
            if getattr(result, "outcome", None) != SUCCESS:
                return Reply(
                    result.outcome,
                    f"❌ Couldn't enable `{entry.key}` "
                    f"({done}/{len(spec.games)} updated): "
                    f"{result.user_message or 'write failed'}.")
            done += 1
        await _refresh_page(req)
        return Reply(SUCCESS,
                     f"✅ {spec.emoji} **{spec.title}** — all {done} games "
                     "enabled (overrides cleared).")
    return enable_all


def _pick_handler(section_key: str):
    async def pick(req) -> Reply:
        """The pick-a-few submit: DIFF the selection against the current
        per-guild state — newly selected → ``enabled=None`` (back to
        default-enabled), newly deselected → ``enabled=False``. Untouched
        games get NO write (no spurious audit rows)."""
        spec = get_section(section_key)
        if spec is None:
            return Reply(SUCCESS, f"❌ Unknown game section `{section_key}`.")
        if not req.guild_id:
            return Reply(SUCCESS, _NEEDS_GUILD)
        selected = {str(v) for v in (req.args.get("values", ()) or ())}
        writes: list[tuple[str, bool | None]] = []
        for entry in spec.games:
            on = await _game_enabled(int(req.guild_id), entry.key)
            if entry.key in selected and not on:
                writes.append((entry.key, None))
            elif entry.key not in selected and on:
                writes.append((entry.key, False))
        enabled_n = disabled_n = 0
        for key, enabled in writes:
            result = await _set_visibility(req, key, enabled)
            if getattr(result, "outcome", None) != SUCCESS:
                return Reply(
                    result.outcome,
                    f"❌ Couldn't update `{key}` "
                    f"({enabled_n + disabled_n}/{len(writes)} applied): "
                    f"{result.user_message or 'write failed'}.")
            if enabled is None:
                enabled_n += 1
            else:
                disabled_n += 1
        if not writes:
            return Reply(SUCCESS,
                         f"{spec.emoji} **{spec.title}** — no changes.")
        await _refresh_page(req)
        return Reply(SUCCESS,
                     f"✅ {spec.emoji} **{spec.title}** — "
                     f"{enabled_n} enabled, {disabled_n} disabled.")
    return pick


# --- the spec (registry-driven — sections must be registered first) -----------


def _selector(spec: GameSectionSpec) -> SelectorSpec:
    return SelectorSpec(
        selector_id=f"pick_{spec.key}", kind=SelectorKind.ENUM,
        options_source=_ensure_options_provider(spec.key),
        placeholder=f"{spec.emoji} {spec.title} — pick the enabled games…",
        min_values=0, max_values=len(spec.games),
        audience_tier="administrator",
        on_select=HandlerRef(f"games.sections_pick_{spec.key}"))


def _enable_all_action(spec: GameSectionSpec) -> PanelActionSpec:
    return PanelActionSpec(
        action_id=f"enable_all_{spec.key}",
        label=f"Enable all — {spec.title}", emoji=spec.emoji,
        style=ActionStyle.SUCCESS, audience_tier="administrator",
        handler=HandlerRef(f"games.sections_enable_all_{spec.key}"))


def games_sections_spec() -> PanelSpec:
    sections = all_sections()
    rows = tuple((f"pick_{s.key}",) for s in sections)
    if sections:
        rows += (tuple(f"enable_all_{s.key}" for s in sections),)
    return PanelSpec(
        panel_id=SECTIONS_PANEL_ID,
        subsystem="games",
        title="🎮 Game sections",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(TextBlock(_DESCRIPTION),
              FieldsBlock(provider=_ensure_fields_provider())),
        selectors=tuple(_selector(s) for s in sections),
        actions=tuple(_enable_all_action(s) for s in sections),
        # opened from the settings hub's group select — ↩ Back returns
        # there (re-resolved at click time, never captured).
        navigation=NavigationSpec(parent=PanelRef("settings.hub"),
                                  show_help=False, show_home=False),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=rows),)),
    )


# --- registration -------------------------------------------------------------


def _register_refs() -> None:
    _ensure_fields_provider()
    for spec in all_sections():
        _ensure_options_provider(spec.key)
        for name, factory in (
                (f"games.sections_enable_all_{spec.key}", _enable_all_handler),
                (f"games.sections_pick_{spec.key}", _pick_handler)):
            if not is_registered(HandlerRef(name)):
                handler(name)(factory(spec.key))
    if not is_registered(PanelRef(SECTIONS_PANEL_ID)):
        panel(SECTIONS_PANEL_ID)(games_sections_spec)


_register_refs()


def install_sections_panel() -> PanelSpec:
    """Register the sections settings panel (fences run here) — called by
    the games manifest AFTER the sections registry is populated.
    Idempotent for identical specs; returns the spec (the manifest
    panels-facet shape)."""
    _register_refs()
    spec = games_sections_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_sections_panel_refs() -> None:
    """Idempotent re-arm of the panel/handler/provider refs."""
    _register_refs()

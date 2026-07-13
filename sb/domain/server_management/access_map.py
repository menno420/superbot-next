"""The 🔓 Access Map subpanel — the shipped staff-hub P1C surface (ORACLE
disbot/views/server_management/access_map.py ``AccessMapView`` +
``build_access_map_embed``) over the ported P1A projection
(:mod:`sb.domain.server_management.access_projection`).

**Display-only** — zero writes, no mutation affordances; every row is a
projection over the existing policy owners (the shipped rule: "it
creates no second permission system").

Shape (shipped copy verbatim):

* the red ADMIN embed titled ``🔓 Access Map``; the description names
  the simulated tier ("Effective feature access for a **Normal member**
  in this channel — a read-only projection over the live policy owners
  (command access · routing · governance · help).");
* the ✅ Allowed (n) / ❌ Denied (n) / ❓ Unresolved (n) fields — denied
  rows carry ONLY the user-safe reason + the deciding axis; fields chunk
  at Discord's 1024-char cap with ``(cont.)`` parts (the shipped
  ``_chunk_field``), so nothing ever silently sheds;
* the pinned "Simulation limits" field (the shipped §16.4 label byte);
* the "Read-only · pick a feature below for the full source chain"
  footer (a literal outside FooterMode's vocabulary — renderer_override,
  the hub-footer precedent);
* row 0: the "Simulate audience…" tier select (the shipped five §6.3
  sub-owner tiers); row 1: the per-feature source-chain drill-down.

Audience simulation rides the declared-tier path (Q-0045 option b /
D-0039 — ``AccessContext.member_tier``, no live member) and every
rendering carries the simulation-limit label.

Ledgered deviations (this slice's PR):
* the shipped drill-down answered with an ephemeral EMBED; the compiled
  handler reply surface is text (the D-0052 text-reply class), so the
  source chain renders as an ephemeral markdown reply carrying the same
  lines (axis → state — detail, the user-safe reason, remediation, the
  limit note);
* the shipped feature select was WINDOWED past Discord's 25-option cap
  (``attach_windowed_select``); the grammar's selector paginates via
  ``page_size`` and clamps at 25 — the 43-row inventory renders its
  first 25 until the windowed-select grammar successor lands (the
  cogmgr page-window precedent names the lane);
* the shipped panel lived on the shared hub message behind a live
  authority re-check; the compiled panel is INVOKER-scoped with the
  administrator floor re-resolved by K6 on every dispatch — the same
  gate, the grammar's home for it.

The tier pick is per (guild, invoker) in-memory view state (the cogmgr
``_cog_pick`` precedent, #331); handlers register at MODULE IMPORT (the
composition-parity invariant).
"""

from __future__ import annotations

import logging
import time
from dataclasses import replace as _dc_replace

from sb.spec.panels import (
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelSpec,
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

logger = logging.getLogger("sb.domain.server_management.access_map")

__all__ = [
    "SIMULATION_LIMIT_NOTE",
    "access_map_spec",
    "ensure_access_map_refs",
    "tier_for",
]

#: the shipped §16.4 label — every simulated rendering carries it (byte
#: verbatim from views/server_management/access_map.py).
SIMULATION_LIMIT_NOTE = (
    "Simulated audience (declared tier) — cannot model live Discord "
    "channel-permission overrides it was not given."
)

#: the shipped §6.3 simulation audiences (sub-owner tiers an operator
#: previews as), verbatim.
_AUDIENCE_TIERS: tuple[tuple[str, str], ...] = (
    ("user", "Normal member"),
    ("trusted", "Trusted user"),
    ("staff", "Staff"),
    ("moderator", "Moderator"),
    ("administrator", "Administrator"),
)

_STATE_GLYPH = {"allow": "✅", "deny": "❌", "unknown": "❓"}
_FIELD_CAP = 1024

#: the shipped footer literal (set_footer) — renderer_override carries it.
_FOOTER = "Read-only · pick a feature below for the full source chain"


def _tier_label(tier: str) -> str:
    return next((label for t, label in _AUDIENCE_TIERS if t == tier), tier)


def _description(tier: str) -> str:
    """The shipped embed description, tier-keyed (build_access_map_embed)."""
    return (
        f"Effective feature access for a **{_tier_label(tier)}** in this "
        "channel — a read-only projection over the live policy owners "
        "(command access · routing · governance · help)."
    )


# --- the invoker's simulated-tier memory (the cogmgr pick precedent) ---------

_tier_pick: dict[tuple[int, int], str] = {}

#: the last projection per (guild, invoker) — the drill-down select's
#: option source and lookup table (display-only view state, never policy).
_last_projection: dict[tuple[int, int], tuple[float, str, tuple]] = {}


def _mem_key(guild_id, user_id) -> tuple[int, int]:
    return (int(guild_id or 0), int(user_id or 0))


def tier_for(guild_id, user_id) -> str:
    """The renderer's read of the invoker's simulated tier (default: the
    shipped opening tier, ``user``)."""
    tier = _tier_pick.get(_mem_key(guild_id, user_id), "user")
    return tier if any(t == tier for t, _ in _AUDIENCE_TIERS) else "user"


def _ctx_ids(ctx) -> tuple[int, int, int | None]:
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    uid = int(getattr(getattr(ctx, "actor", None), "user_id", 0) or 0)
    channel_id = getattr(ctx, "channel_id", None)
    return gid, uid, channel_id


async def _projection(ctx) -> tuple:
    """Run (or reuse this render pass's) declared-tier projection for the
    invoker's current tier pick — the shipped ``_simulated_context`` path."""
    from sb.domain.server_management.access_projection import (
        AccessContext,
        project_access_map,
    )

    gid, uid, channel_id = _ctx_ids(ctx)
    tier = tier_for(gid, uid)
    key = _mem_key(gid, uid)
    cached = _last_projection.get(key)
    if cached is not None:
        stamp, cached_tier, decisions = cached
        if cached_tier == tier and time.monotonic() - stamp < 1.0:
            # same render pass (fields + options providers share one run)
            return decisions
    decisions = await project_access_map(AccessContext(
        guild_id=gid or None,
        channel_id=channel_id,
        member_tier=tier,
        invocation_type="prefix",
    ))
    _last_projection[key] = (time.monotonic(), tier, decisions)
    return decisions


def _chunk_field(fields: list[tuple[str, str]], name: str,
                 lines: list[str]) -> None:
    """The shipped ``_chunk_field``: add ``lines`` as one or more fields,
    respecting the 1024-char cap — ``(cont.)`` parts, nothing sheds."""
    if not lines:
        return
    chunk: list[str] = []
    size = 0
    part = 1
    for line in lines:
        if size + len(line) + 1 > _FIELD_CAP and chunk:
            fields.append((name if part == 1 else f"{name} (cont.)",
                           "\n".join(chunk)))
            chunk, size, part = [], 0, part + 1
        chunk.append(line)
        size += len(line) + 1
    fields.append((name if part == 1 else f"{name} (cont.)",
                   "\n".join(chunk)))


async def _access_map_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped embed body: Allowed / Denied / Unresolved buckets +
    the pinned Simulation limits field (build_access_map_embed verbatim)."""
    decisions = await _projection(ctx)
    allowed = [d.feature for d in decisions if d.effective == "allow"]
    unknown = [d.feature for d in decisions if d.effective == "unknown"]
    denied_lines = []
    for d in decisions:
        if d.effective != "deny":
            continue
        axis = d.deciding_axis.value if d.deciding_axis else "?"
        reason = d.reason.safe_text if d.reason else "denied"
        denied_lines.append(f"❌ **{d.feature}** — {reason} *(axis: {axis})*")

    fields: list[tuple[str, str]] = []
    if allowed:
        _chunk_field(fields, f"✅ Allowed ({len(allowed)})",
                     ["· ".join(allowed)])
    _chunk_field(fields, f"❌ Denied ({len(denied_lines)})", denied_lines)
    if unknown:
        _chunk_field(fields, f"❓ Unresolved ({len(unknown)})",
                     ["· ".join(unknown)])
    fields.append(("Simulation limits", SIMULATION_LIMIT_NOTE))
    return tuple(fields)


async def _tier_options(ctx) -> tuple[dict, ...]:
    """The shipped ``_AudienceTierSelect`` options — the current pick
    renders as the select default."""
    gid, uid, _ = _ctx_ids(ctx)
    current = tier_for(gid, uid)
    return tuple(
        {"label": label, "value": tier, "default": tier == current}
        for tier, label in _AUDIENCE_TIERS
    )


async def _feature_options(ctx) -> tuple[dict, ...]:
    """The shipped drill-down options: ``<glyph> <feature>`` over the
    feature key (attach-windowed-select option shape)."""
    decisions = await _projection(ctx)
    return tuple(
        {"label": f"{_STATE_GLYPH.get(d.effective, '·')} {d.feature}"[:100],
         "value": d.feature}
        for d in decisions
    )


# --- the panel ----------------------------------------------------------------


def access_map_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="server_management.access_map",
        subsystem="server_management",
        title="🔓 Access Map",
        # the shipped subpanel lived behind the admin hub's ephemeral
        # surface; INVOKER keeps the slash open ephemeral (hub precedent).
        audience=Audience.INVOKER,
        # the shipped ADMIN_COLOR — discord.Color.red() (ui_constants.py).
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(
            # the default-tier byte; the override re-keys it to the pick.
            TextBlock(_description("user")),
            FieldsBlock(provider=ProviderRef(
                "server_management.access_map_fields")),
        ),
        selectors=(
            SelectorSpec(
                selector_id="am_tier", kind=SelectorKind.ENUM,
                options_source=ProviderRef(
                    "server_management.access_map_tiers"),
                placeholder="Simulate audience…",       # shipped byte
                audience_tier="administrator",
                on_select=HandlerRef("server_management.access_map_tier")),
            SelectorSpec(
                selector_id="am_feature", kind=SelectorKind.SUBSYSTEM,
                options_source=ProviderRef(
                    "server_management.access_map_features"),
                placeholder="Inspect a feature's source chain…",  # shipped
                audience_tier="administrator",
                on_select=HandlerRef(
                    "server_management.access_map_inspect")),
        ),
        # the compiled escape: the grammar nav back to the hub (the shipped
        # subpanel carried the hub's back button across re-renders).
        navigation=NavigationSpec(parent=PanelRef("server_management.hub"),
                                  show_help=False, show_home=False),
        renderer_override=HandlerRef("server_management.render_access_map"),
        justification=(
            "the shipped subpanel footer is the literal 'Read-only · pick "
            "a feature below for the full source chain' (access_map.py "
            "set_footer) — outside FooterMode's none/subsystem/provenance "
            "vocabulary — and the description is TIER-keyed state copy "
            "('Effective feature access for a **<tier>** …', re-rendered "
            "per audience pick) — the cogmgr selection-footer precedent. "
            "The override delegates to the grammar renderer and adjusts "
            "only those two embed surfaces; fields, selectors, navigation "
            "and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("am_tier",),
            ("am_feature",),
        )),)),
    )


async def _render_access_map(spec: PanelSpec, ctx) -> object:
    """Grammar render + the two shipped state-keyed embed surfaces (see
    justification): the tier-keyed description and the footer literal."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    gid, uid, _ = _ctx_ids(ctx)
    tier = tier_for(gid, uid)
    return _dc_replace(
        rendered,
        embed=_dc_replace(rendered.embed,
                          description=_description(tier),
                          footer=_FOOTER))


# --- handlers -------------------------------------------------------------------


def _format_source_chain(decision) -> str:
    """The shipped drill-down embed's lines as an ephemeral markdown reply
    (ledgered deviation: text, not an embed — module docstring)."""
    lines = [f"**Source chain — {decision.feature}**"]
    lines += [
        f"`{o.axis.value}` → **{o.state}**"
        + (f" — {o.detail}" if o.detail else "")
        for o in decision.source_chain
    ]
    if decision.reason is not None:
        lines.append(f"User-safe reason: {decision.reason.safe_text}")
    if decision.remediation:
        lines.append(f"Remediation: {decision.remediation}")
    lines.append(f"*{SIMULATION_LIMIT_NOTE}*")
    return "\n".join(lines)[:2000]


def _register_refs() -> None:
    from sb.kernel.interaction.handler_kit import Reply
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import handler

    if not is_registered(PanelRef("server_management.access_map")):
        panel("server_management.access_map")(access_map_spec)
    if not is_registered(HandlerRef("server_management.render_access_map")):
        handler("server_management.render_access_map")(_render_access_map)
    for name, fn in (
        ("server_management.access_map_fields", _access_map_fields),
        ("server_management.access_map_tiers", _tier_options),
        ("server_management.access_map_features", _feature_options),
    ):
        if not is_registered(ProviderRef(name)):
            provider(name)(fn)

    if is_registered(HandlerRef("server_management.access_map_tier")):
        return

    def _req_key(req) -> tuple[int, int]:
        return _mem_key(req.guild_id, getattr(req.actor, "user_id", 0))

    async def _reopen(req) -> None:
        import dataclasses

        from sb.kernel.panels.engine import open_panel

        await open_panel(PanelRef("server_management.access_map"),
                         dataclasses.replace(req, args=dict(req.args)))

    @handler("server_management.access_map_tier")
    async def access_map_tier(req):
        """The shipped ``_AudienceTierSelect`` callback: stash the pick,
        re-render the panel in place for the new simulated audience."""
        values = tuple(req.args.get("values") or ())
        picked = str(values[0]) if values else ""
        if not any(t == picked for t, _ in _AUDIENCE_TIERS):
            # stale/unknown option — the polite terminal, never a crash.
            return Reply(SUCCESS, "That audience tier is not available.")
        key = _req_key(req)
        _tier_pick[key] = picked
        _last_projection.pop(key, None)      # force a fresh projection
        await _reopen(req)
        return Reply(SUCCESS, None)

    @handler("server_management.access_map_inspect")
    async def access_map_inspect(req):
        """The shipped per-feature drill-down: the decision's full source
        chain as an ephemeral reply (a genuine detail answer, not a panel
        re-render)."""
        values = tuple(req.args.get("values") or ())
        picked = str(values[0]) if values else ""
        key = _req_key(req)
        cached = _last_projection.get(key)
        decisions = cached[2] if cached is not None else ()
        decision = next((d for d in decisions if d.feature == picked), None)
        if decision is None:
            # evicted view state (restart) — re-derive the one feature
            # fresh rather than stranding the click.
            decision = await _fresh_decision(req, picked)
        if decision is None:
            # the shipped copy, verbatim (a stale/unknown pick).
            return Reply(SUCCESS,
                         "That feature is not in the current projection.")
        return Reply(SUCCESS, _format_source_chain(decision))

    async def _fresh_decision(req, feature_key: str):
        from sb.domain.server_management.access_projection import (
            AccessContext,
            feature_inventory,
            resolve_feature_access,
        )

        feature = next((f for f in feature_inventory()
                        if f.subsystem == feature_key), None)
        if feature is None:
            return None
        gid, uid = _req_key(req)
        return await resolve_feature_access(feature, AccessContext(
            guild_id=gid or None,
            channel_id=getattr(req, "channel_id", None),
            member_tier=tier_for(gid, uid),
            invocation_type="prefix",
        ))


_register_refs()


def ensure_access_map_refs() -> None:
    _register_refs()

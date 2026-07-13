"""The 👁 Help Preview subpanel — the shipped staff-hub P1C surface
(ORACLE disbot/views/server_management/access_map.py ``HelpPreviewView``
+ ``build_help_preview_embed`` over services/help_projection.py
``project_help_with_execution``), ported as a pure consumer of the
slice-A access projection.

**Display-only** — zero writes; the live Help command stays the renderer
of record. For a simulated audience tier the panel buckets every feature
per the shipped §16.4 honest-rendering rule:

* **📣 Advertised** — Help shows it and execution is not verified-denied
  (``allow`` AND ``unknown`` both advertise: the model never hides what
  it could not verify-deny — the shipped rule verbatim);
* **🔒 Shown as locked** — Help shows it but a gating axis denies
  execution; the line carries ONLY the user-safe reason
  (``safe_locked_reason`` — never an internal string);
* **🙈 Hidden** — Help itself hides it for this audience.

THE COMPILED HIDING RULE (the honesty core — the panel must never
disagree with live Help about what hides, the shipped Tier-2 audit
lesson): the compiled help index carries NO governance tier filter
(D-0054 judgment call 3 — authority re-resolves at dispatch; the
tier-filtered index rides the D-0026 overlay successor lane), so the
ONLY live hide is the category staff-gate (the moderation/admin mother
hubs — sb/domain/help/categories.py). A GOVERNANCE denial therefore
renders as *shown-as-locked* here (the compiled Help really does
advertise it), where the shipped bot — whose Help consumed governance —
bucketed it hidden. When the governance-filtered index ports, this
panel's hidden bucket inherits it by construction (it reads the same
axis). Overlay renames + orphaned-overlay reporting arrive with the
D-0026 overlay store (slice C).

Ledgered deviations (this slice's PR): the hidden-bucket annotation is
``(staff-gate)`` — the compiled hide owner — instead of the shipped
``(governance)``/``(display)`` pair whose owners are not the compiled
index's; entity labels are the stable subsystem keys (the shipped label
was also the key until an overlay rename applied — none can, yet).

The tier pick is per (guild, invoker) in-memory view state shared with
the Access Map's shell vocabulary (the cogmgr pick precedent); handlers
register at MODULE IMPORT (the composition-parity invariant).
"""

from __future__ import annotations

import logging
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

logger = logging.getLogger("sb.domain.server_management.help_preview")

__all__ = [
    "ensure_help_preview_refs",
    "help_preview_spec",
    "preview_tier_for",
]

#: the shipped audience roster + §16.4 label — one vocabulary with the
#: Access Map (both shipped panels shared `AUDIENCE_TIERS` and the note).
from sb.domain.server_management.access_map import (  # noqa: E402
    AUDIENCE_TIERS,
    SIMULATION_LIMIT_NOTE,
    chunk_field,
    tier_label,
)

#: the shipped footer literal (build_help_preview_embed set_footer).
_FOOTER = "Read-only preview · simulated audience"


def _description(tier: str) -> str:
    """The shipped embed description, tier-keyed."""
    return (
        f"What Help advertises to a **{tier_label(tier)}** in this "
        "channel. Display-only — the live Help command stays the renderer "
        "of record."
    )


# --- the invoker's simulated-tier memory (own pick, shared vocabulary) --------

_tier_pick: dict[tuple[int, int], str] = {}


def _mem_key(guild_id, user_id) -> tuple[int, int]:
    return (int(guild_id or 0), int(user_id or 0))


def preview_tier_for(guild_id, user_id) -> str:
    """The renderer's read of the invoker's simulated tier (default: the
    shipped opening tier, ``user``)."""
    tier = _tier_pick.get(_mem_key(guild_id, user_id), "user")
    return tier if any(t == tier for t, _ in AUDIENCE_TIERS) else "user"


def _ctx_ids(ctx) -> tuple[int, int, int | None]:
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    uid = int(getattr(getattr(ctx, "actor", None), "user_id", 0) or 0)
    return gid, uid, getattr(ctx, "channel_id", None)


def _is_help_hidden(subsystem: str, tier: str) -> bool:
    """The compiled index's ONLY hide: the category staff-gate, simulated
    as ``tier >= moderator`` (the slice-A help-axis rule)."""
    from sb.domain.governance.tiers import tier_at_or_above
    from sb.domain.help import categories as cats

    category = cats.category_by_key(cats.category_for_subsystem(subsystem))
    if category is None or not category.staff_only:
        return False
    try:
        return not tier_at_or_above(tier, "moderator")
    except (ValueError, KeyError):
        return True


async def _help_preview_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped embed body: Advertised / Shown-as-locked / Hidden
    buckets + the pinned Simulation limits field."""
    from sb.domain.server_management.access_projection import (
        AccessContext,
        project_access_map,
        safe_locked_reason,
    )

    gid, uid, channel_id = _ctx_ids(ctx)
    tier = preview_tier_for(gid, uid)
    decisions = await project_access_map(AccessContext(
        guild_id=gid or None,
        channel_id=channel_id,
        member_tier=tier,
        invocation_type="prefix",
    ))

    advertised: list[str] = []
    locked_lines: list[str] = []
    hidden: list[str] = []
    for d in decisions:
        if _is_help_hidden(d.feature, tier):
            hidden.append(f"{d.feature} *(staff-gate)*")
        elif d.effective == "deny":
            reason = (d.reason if d.reason is not None
                      else safe_locked_reason(None))
            locked_lines.append(f"🔒 **{d.feature}** — {reason.safe_text}")
        else:
            # allow AND unknown both advertise — the model never hides
            # what it could not verify-deny (shipped rule verbatim).
            advertised.append(d.feature)

    fields: list[tuple[str, str]] = []
    if advertised:
        chunk_field(fields, f"📣 Advertised ({len(advertised)})",
                    ["· ".join(advertised)])
    chunk_field(fields, f"🔒 Shown as locked ({len(locked_lines)})",
                locked_lines)
    if hidden:
        chunk_field(fields, f"🙈 Hidden ({len(hidden)})",
                    ["· ".join(hidden)])
    fields.append(("Simulation limits", SIMULATION_LIMIT_NOTE))
    return tuple(fields)


async def _tier_options(ctx) -> tuple[dict, ...]:
    """The shipped ``_AudienceTierSelect`` options — the current pick
    renders as the select default."""
    gid, uid, _ = _ctx_ids(ctx)
    current = preview_tier_for(gid, uid)
    return tuple(
        {"label": label, "value": tier, "default": tier == current}
        for tier, label in AUDIENCE_TIERS
    )


# --- the panel ----------------------------------------------------------------


def help_preview_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="server_management.help_preview",
        subsystem="server_management",
        title="👁 Help Preview",
        audience=Audience.INVOKER,
        # the shipped ADMIN_COLOR — discord.Color.red() (ui_constants.py).
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(
            # the default-tier byte; the override re-keys it to the pick.
            TextBlock(_description("user")),
            FieldsBlock(provider=ProviderRef(
                "server_management.help_preview_fields")),
        ),
        selectors=(
            SelectorSpec(
                selector_id="hp_tier", kind=SelectorKind.ENUM,
                options_source=ProviderRef(
                    "server_management.help_preview_tiers"),
                placeholder="Simulate audience…",       # shipped byte
                audience_tier="administrator",
                on_select=HandlerRef(
                    "server_management.help_preview_tier")),
        ),
        navigation=NavigationSpec(parent=PanelRef("server_management.hub"),
                                  show_help=False, show_home=False),
        renderer_override=HandlerRef(
            "server_management.render_help_preview"),
        justification=(
            "the shipped subpanel footer is the literal 'Read-only "
            "preview · simulated audience' (access_map.py set_footer) — "
            "outside FooterMode's none/subsystem/provenance vocabulary — "
            "and the description is TIER-keyed state copy ('What Help "
            "advertises to a **<tier>** …', re-rendered per audience "
            "pick) — the access_map/cogmgr precedent. The override "
            "delegates to the grammar renderer and adjusts only those two "
            "embed surfaces; fields, selector, navigation and layout stay "
            "declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(("hp_tier",),)),)),
    )


async def _render_help_preview(spec: PanelSpec, ctx) -> object:
    """Grammar render + the two shipped state-keyed embed surfaces (see
    justification): the tier-keyed description and the footer literal."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    gid, uid, _ = _ctx_ids(ctx)
    tier = preview_tier_for(gid, uid)
    return _dc_replace(
        rendered,
        embed=_dc_replace(rendered.embed,
                          description=_description(tier),
                          footer=_FOOTER))


# --- handlers -------------------------------------------------------------------


def _register_refs() -> None:
    from sb.kernel.interaction.handler_kit import Reply
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import handler

    if not is_registered(PanelRef("server_management.help_preview")):
        panel("server_management.help_preview")(help_preview_spec)
    if not is_registered(
            HandlerRef("server_management.render_help_preview")):
        handler("server_management.render_help_preview")(
            _render_help_preview)
    for name, fn in (
        ("server_management.help_preview_fields", _help_preview_fields),
        ("server_management.help_preview_tiers", _tier_options),
    ):
        if not is_registered(ProviderRef(name)):
            provider(name)(fn)

    if is_registered(HandlerRef("server_management.help_preview_tier")):
        return

    @handler("server_management.help_preview_tier")
    async def help_preview_tier(req):
        """The shipped ``_AudienceTierSelect`` callback: stash the pick,
        re-render the panel in place for the new simulated audience."""
        import dataclasses

        from sb.kernel.panels.engine import open_panel

        values = tuple(req.args.get("values") or ())
        picked = str(values[0]) if values else ""
        if not any(t == picked for t, _ in AUDIENCE_TIERS):
            # stale/unknown option — the polite terminal, never a crash.
            return Reply(SUCCESS, "That audience tier is not available.")
        _tier_pick[_mem_key(req.guild_id,
                            getattr(req.actor, "user_id", 0))] = picked
        await open_panel(PanelRef("server_management.help_preview"),
                         dataclasses.replace(req, args=dict(req.args)))
        return Reply(SUCCESS, None)


_register_refs()


def ensure_help_preview_refs() -> None:
    _register_refs()

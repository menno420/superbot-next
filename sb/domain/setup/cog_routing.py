"""The COG-ROUTING section flow (the routing-ticket slice — the FINAL
section-flow slice), ported from the oracle (menno420/superbot, read
from the LOCAL oracle clone: views/setup/sections/cog_routing.py +
services/cog_routing_profiles.py + utils/subsystem_registry.py's
consumed visibility read + utils/channel_classify.py's consumed
game/mining tag pair):

* the SCOPE WALKER (``_ScopeSelect`` → ``_CategoryPickSelect`` /
  ``_ChannelPickSelect`` → the cog pick → ``_EnableDisableSelect``,
  flow verbatim): Server default / Category override / Channel
  override; a guild pick reveals the cog select directly,
  category/channel picks reveal the native channel picker first; the
  cog pick reveals Enable / Disable, and THAT pick stages ONE
  ``set_cog_routing`` op and answers the shipped staged/pending
  confirmation;
* the PROFILE BATCH PICKER (``_RoutingProfileSelect`` + the four-
  profile catalogue, copy verbatim): games → game channels only /
  economy → economy+game channels only / moderation → staff channels
  only / recommended (all three in one pass) — each profile disables
  the cog at guild scope and re-enables it on detected matching
  channels (``likely_game`` / ``likely_mining`` /
  ``likely_mod``+``likely_admin``+``likely_mod_log`` name tags);
* NO auto-recommended path (cog_routing.run:
  ``recommended_ops_builder=None`` — "routing changes are server-wide
  and can silently break the bot's behaviour if misapplied");
* **Final Review remains the only apply gate** — staging only ever
  writes draft rows.

Kernel-idiom divergences, ledgered (the section_card.py doctrine):

* the ``set_cog_routing`` op kind is REGISTERED onto the audited K7
  ``routing.set_policy`` compound op (the compound-ops slice landed the
  routing port: ``command_routing_policy`` migration 0054 + the
  sb/domain/server_management/routing.py resolver/store + the op in
  server_management/ops.py — the access_projection axis-3 "NOT PORTED"
  ledger flipped true), so staged rows are draftable AND appliable
  through the fail-closed K9 registry. The staged payload carries the
  full ``services.command_routing.set_policy`` param shape and the
  dispatcher reads it back unchanged (the design held);
* the COG PICKER rides the windowed-select grammar successor
  (``SelectorSpec(windowed=True)`` → the kernel selectwindow engine):
  the full 43-row harvest pages at Discord's 25-option cap with
  engine-injected ◀ Prev / Next ▶ nav (``nav:selwin:`` ids) — the
  oracle's ``PaginatedSelectView`` posture restored; the ad-hoc
  first-25 window this module shipped with (the access_map precedent,
  the #1040 truncation class) is retired. The list is the shipped
  43-row subsystem harvest
  (sb/domain/governance/registry.SUBSYSTEM_META — all rows
  visibility-normal, the oracle ``visibility_mode != "internal"``
  filter passes everything), sorted, presented with the shipped
  display_name + emoji (help/categories.SUBSYSTEM_PRESENTATION; the
  harvest carries no description facet, so options render without
  one — the oracle's ``description or None`` empty branch);
* ONE native channel picker serves both the category and the channel
  scope (placeholder patched per scope) — the grammar's CHANNEL
  selector carries no channel-type filter (the cleanup-flow ledger);
* the oracle opened each step as a fresh ephemeral view; the detail
  folds them stepwise onto one panel (the cleanup-detail precedent),
  and the final ``_EnableDisableSelect`` rides as TWO declared
  state-revealed BUTTONS (✅ Enable · 🚫 Disable, the shipped option
  labels/emoji as button faces) sharing the back-step row — a fifth
  select would need a sixth action row past the compiler's five-row
  page cap (the roles-detail declared-buttons precedent; the shipped
  per-cog ``Enable or disable {cog}…`` placeholder byte has no button
  carrier — the staging confirmation carries the cog instead);
* profile channel detection walks the advisor's installed channel
  index (plan._channel_index — the cleanup-profile seam); a headless
  runtime detects nothing and the profiles degrade to their
  guild-scope disable row (the cleanup silent_bot fallback class);
* profile rows ride ``stage_custom`` so the label carries the
  ``[cog_routing] `` provenance prefix + the shipped
  ``[profile:{slug}] …`` tail (the cleanup-profile precedent);
* staged K9 rows carry no oracle metadata dict (source/confidence/
  risk/rollback_note) — the final_review.py ledger note's class.

NO GOLDEN drives any of these components (the panels.py module pin);
the oracle SOURCES pin the copy, and every golden-pinned OPEN render
stays byte-identical.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = [
    "COG_ROUTING_DETAIL_PANEL_ID",
    "CogRoutingProfile",
    "PROFILES",
    "build_cog_routing_embed",
    "cog_routing_detail_spec",
    "ensure_setup_cog_routing_refs",
    "get_routing_profile",
    "operator_visible_cogs",
    "routing_profile_ops",
    "reset_cog_routing_state_for_tests",
]

logger = logging.getLogger("sb.domain.setup")

SLUG = "cog_routing"

COG_ROUTING_DETAIL_PANEL_ID = "setup.cog_routing_detail"

_SCOPE_OPTIONS_PROVIDER = "setup.cog_routing_scope_options"
_PROFILE_OPTIONS_PROVIDER = "setup.cog_routing_profile_options"
_COG_OPTIONS_PROVIDER = "setup.cog_routing_cog_options"

#: the shipped card copy, verbatim (cog_routing.run's ``detected``).
_DETECTED_STATE = (
    "Cogs are enabled in every channel by default. "
    "Click Customize to apply a routing profile (e.g. games-only-in-game-channels) "
    "or set a per-scope override.")

#: Discord's single-select option cap — the oracle paginated past it
#: (``_COG_PAGE_SIZE = 25``); the declared ``windowed`` ENUM select pages
#: at it through the kernel selectwindow engine (module docstring ledger).
_COG_PAGE_SIZE = 25


# --- the operator-visible cog list (cog_routing._operator_visible_cogs, ported) ---------

def operator_visible_cogs() -> tuple[str, ...]:
    """Every SUBSYSTEM_META key whose visibility is not internal —
    the shipped 43-row harvest carries no internal rows, so the oracle
    filter passes everything; sorted (the shipped contract)."""
    from sb.domain.governance.registry import SUBSYSTEM_META

    return tuple(sorted(SUBSYSTEM_META.keys()))


def _cog_option(name: str, *, default: bool = False) -> dict:
    """One cog option — the shipped display_name/emoji presentation
    (help/categories.SUBSYSTEM_PRESENTATION; no description facet in
    the harvest — the oracle ``description or None`` empty branch)."""
    from sb.domain.help.categories import SUBSYSTEM_PRESENTATION

    display, emoji = SUBSYSTEM_PRESENTATION.get(name, (name, None))
    option = {"label": str(display)[:100], "value": name,
              "default": default}
    if emoji:
        option["emoji"] = emoji
    return option


# --- the consumed game/mining classifier pair (utils/channel_classify.py, verbatim) -----

_GAME_MINING_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "likely_mining": (
        re.compile(r"\bmining\b"),
        re.compile(r"\bmine\b"),
    ),
    "likely_game": (
        re.compile(r"\bgames?\b"),
        re.compile(r"\bbet(?:s|ting)?\b"),
        re.compile(r"\bcasino\b"),
        re.compile(r"\bblackjack\b"),
        re.compile(r"\brps\b"),
        re.compile(r"\bdeathmatch\b"),
        re.compile(r"\btournament\b"),
    ),
}


def _classify(name: str) -> set[str]:
    """The profile builders' tag read: the cleanup-carried subset
    (likely_mod / likely_admin / likely_mod_log / likely_bot_cmd) plus
    the game/mining pair carried here (patterns verbatim)."""
    from sb.domain.setup.cleanup import classify_channel_name

    tags = set(classify_channel_name(name or ""))
    lowered = (name or "").lower()
    for tag, patterns in _GAME_MINING_PATTERNS.items():
        if lowered and any(p.search(lowered) for p in patterns):
            tags.add(tag)
    return tags


# --- staged-op builder -------------------------------------------------------------------

_SET_COG_ROUTING_OP_KIND = "set_cog_routing"


def _register_set_cog_routing_op_kind() -> None:
    """Bind the ``set_cog_routing`` op kind onto the audited K7
    ``routing.set_policy`` compound op (the module docstring's named
    follow-up, landed by the compound-ops slice): read-old → ON CONFLICT
    upsert → central audit with the real prev_value — the oracle
    ``command_routing.set_policy`` route (setup_operations.py:1160 →
    _apply_set_cog_routing:1559)."""
    from sb.kernel.draft.registry import OP_KINDS, OpKindBinding
    from sb.spec.events import FieldSpec
    from sb.spec.refs import WorkflowRef

    binding = OpKindBinding(
        op_kind=_SET_COG_ROUTING_OP_KIND,
        workflow_ref=WorkflowRef("routing.set_policy"),
        payload_schema=(FieldSpec("name", "str"),
                        FieldSpec("scope_type", "str"),
                        FieldSpec("scope_id", "int", required=False),
                        FieldSpec("cog_name", "str"),
                        FieldSpec("enabled", "bool"),
                        FieldSpec("target_name", "str", required=False)),
        is_resource_create=False)
    try:
        OP_KINDS.register(binding)
    except ValueError as exc:
        if "bound twice" not in str(exc):
            raise


def _routing_op(*, scope_kind: str, scope_id: int | None, scope_name: str,
                cog_name: str, enabled: bool,
                label_body: str | None = None):
    """One ``set_cog_routing`` StagedSectionOp: the full
    ``command_routing.set_policy`` param shape (scope_type / scope_id /
    cog_name / enabled) plus the review-renderer ride-alongs
    (target_name; the extra keys ride ABOVE the dispatcher's
    minimum — the stage_accepted precedent). ``name`` keys the
    replace-on-conflict slot per (scope, cog) — a re-picked flag
    replaces, never duplicates (the oracle rollback note: "Re-stage
    with the opposite flag"); the guild scope spells its slot ``guild``
    exactly like the oracle audit target
    (``{scope_type}:{scope_id if scope_id is not None else 'guild'}:
    {cog_name}``)."""
    from sb.domain.setup.section_card import StagedSectionOp

    _register_set_cog_routing_op_kind()

    slot_scope = scope_id if scope_id is not None else "guild"
    default_label = (f"cog_routing.{scope_kind}({scope_name}).{cog_name} = "
                     f"{'enabled' if enabled else 'disabled'}")
    return StagedSectionOp(
        op_kind="set_cog_routing", subsystem="cog_routing",
        payload={"name": f"{scope_kind}:{slot_scope}:{cog_name}",
                 "scope_type": scope_kind,
                 "scope_id": (int(scope_id) if scope_id is not None
                              else None),
                 "cog_name": cog_name,
                 "enabled": bool(enabled),
                 "target_name": scope_name},
        label_body=label_body or default_label)


# --- the profile catalogue (services/cog_routing_profiles.py, copy verbatim) --------------

@dataclass(frozen=True)
class CogRoutingProfile:
    """One named routing bundle (cog_routing_profiles.CogRoutingProfile
    — the builder rides the (id, name) channel listing)."""

    slug: str
    display_name: str
    description: str
    kind: str  # games | economy | moderation | recommended


PROFILES: dict[str, CogRoutingProfile] = {
    "games_in_game_channels": CogRoutingProfile(
        slug="games_in_game_channels",
        display_name="Games → game channels only",
        description=(
            "Disable the games cog at guild scope and re-enable it on "
            "each detected `likely_game` channel."),
        kind="games"),
    "economy_in_economy_channels": CogRoutingProfile(
        slug="economy_in_economy_channels",
        display_name="Economy → economy/game channels only",
        description=(
            "Disable the economy cog at guild scope and re-enable on "
            "channels matching the game/mining classifiers."),
        kind="economy"),
    "moderation_to_staff": CogRoutingProfile(
        slug="moderation_to_staff",
        display_name="Moderation → staff channels only",
        description=(
            "Disable the moderation cog at guild scope and re-enable "
            "on detected mod / admin / staff channels."),
        kind="moderation"),
    "recommended_by_name": CogRoutingProfile(
        slug="recommended_by_name",
        display_name="Recommended (all cogs by channel name)",
        description=(
            "Apply games / economy / moderation routing in one pass — "
            "each cog disabled at guild scope and re-enabled only in "
            "channels whose name matches its intent."),
        kind="recommended"),
}


def get_routing_profile(slug: str) -> CogRoutingProfile | None:
    return PROFILES.get(slug)


def _profile_label(slug: str, op) -> str:
    """The shipped profile staging label, verbatim
    (_RoutingProfileSelect.callback's ``[profile:{slug}]
    cog_routing.{target_kind}({target_name}).{value} = {enabled_str}``
    over the ported payload keys)."""
    payload = op.payload
    enabled_str = "enabled" if payload.get("enabled") else "disabled"
    return (f"[profile:{slug}] cog_routing.{payload['scope_type']}"
            f"({payload['target_name']}).{payload['cog_name']} = "
            f"{enabled_str}")


async def routing_profile_ops(profile: CogRoutingProfile, guild_id: int) -> list:
    """cog_routing_profiles' builders, ported (deterministic,
    side-effect free — same guild + same channel set → same op order):
    the guild-scope disable row first, then the detected per-channel
    re-enables (per-tag dedup on the channel id, the shipped ``seen``
    sets)."""
    from sb.domain.setup.cleanup import _guild_channels, _guild_name

    guild_name = await _guild_name(guild_id)
    channels = await _guild_channels(guild_id)

    def _bundle(cog: str, tags: tuple[str, ...]) -> list:
        ops = [_routing_op(scope_kind="guild", scope_id=None,
                           scope_name=guild_name, cog_name=cog,
                           enabled=False)]
        seen: set[int] = set()
        for tag in tags:
            for channel in channels:
                if int(channel.id) in seen:
                    continue
                if tag in _classify(str(channel.name)):
                    seen.add(int(channel.id))
                    ops.append(_routing_op(
                        scope_kind="channel", scope_id=int(channel.id),
                        scope_name=str(channel.name), cog_name=cog,
                        enabled=True))
        return ops

    if profile.kind == "games":
        ops = _bundle("games", ("likely_game",))
    elif profile.kind == "economy":
        ops = _bundle("economy", ("likely_game", "likely_mining"))
    elif profile.kind == "moderation":
        ops = _bundle("moderation",
                      ("likely_mod", "likely_admin", "likely_mod_log"))
    elif profile.kind == "recommended":
        ops = (_bundle("games", ("likely_game",))
               + _bundle("economy", ("likely_game", "likely_mining"))
               + _bundle("moderation",
                         ("likely_mod", "likely_admin", "likely_mod_log")))
    else:
        return []
    from dataclasses import replace as _replace

    return [_replace(op, label_body=_profile_label(profile.slug, op))
            for op in ops]


# --- the entry embed (build_cog_routing_embed, bytes verbatim) -----------------------------

def build_cog_routing_embed():
    from sb.kernel.panels.render import RenderedEmbed

    return RenderedEmbed(
        title="🧭 Cog routing",
        description=(
            "Enable or disable cogs per scope.  The resolver walks "
            "**channel → category → server → default-true** — a fresh "
            "server has every cog enabled and routing only restricts.  "
            "Each pick stages a `set_cog_routing` operation; nothing "
            "applies until Final review."),
        fields=(
            ("How to use",
             ("1. Pick a scope.\n"
              "2. (Category / channel scopes) pick the target.\n"
              "3. Pick the cog.\n"
              "4. Pick Enable or Disable."),
             False),
        ),
        footer="Cogs default to enabled; this section creates exceptions.",
        style_token="blurple")


# --- flow state -----------------------------------------------------------------------------

#: guild:user → the picked scope kind ("guild" | "category" | "channel").
_PICKED_SCOPE: dict[str, str] = {}
#: guild:user → the picked override target (id, name).
_PICKED_TARGET: dict[str, tuple[int, str]] = {}
#: guild:user → the picked cog name.
_PICKED_COG: dict[str, str] = {}


def _key(req_or_ctx) -> str:
    return (f"{int(req_or_ctx.guild_id or 0)}:"
            f"{int(getattr(req_or_ctx.actor, 'user_id', 0) or 0)}")


def reset_cog_routing_state_for_tests() -> None:
    _PICKED_SCOPE.clear()
    _PICKED_TARGET.clear()
    _PICKED_COG.clear()


# --- the detail panel -------------------------------------------------------------------------

def cog_routing_detail_spec():
    """CogRoutingSectionView + the stepwise pick sub-views folded onto
    one panel: the scope select (row 0), the profile batch picker
    (row 1, the shipped ``cog_routing_section_profile`` custom_id),
    the state-dependent native target picker (row 2 — category/channel
    scopes only), the cog select (row 3), and the state-revealed
    ✅ Enable · 🚫 Disable buttons (module docstring ledger — the
    oracle ``_EnableDisableSelect`` as declared button faces) sharing
    row 4 with the wizard-origin ↩ Back to step button."""
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        NavigationSpec, PageSpec, PanelActionSpec, PanelSpec, SelectorKind,
        SelectorSpec,
    )
    from sb.spec.refs import HandlerRef, ProviderRef

    return PanelSpec(
        panel_id=COG_ROUTING_DETAIL_PANEL_ID,
        subsystem="setup",
        title="🧭 Cog routing",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="routing_scope", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.cog_routing_scope_pick"),
                options_source=ProviderRef(_SCOPE_OPTIONS_PROVIDER),
                placeholder="Pick a scope…"),
            SelectorSpec(
                selector_id="routing_profile", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.cog_routing_profile_pick"),
                options_source=ProviderRef(_PROFILE_OPTIONS_PROVIDER),
                placeholder="Apply a routing profile (batch action)…",
                custom_id_override="cog_routing_section_profile"),
            SelectorSpec(
                selector_id="routing_target", kind=SelectorKind.CHANNEL,
                on_select=HandlerRef("setup.cog_routing_target_pick"),
                placeholder="Pick a channel…"),
            SelectorSpec(
                selector_id="routing_cog", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.cog_routing_cog_pick"),
                options_source=ProviderRef(_COG_OPTIONS_PROVIDER),
                placeholder="Pick a cog…",
                # the windowed-select grammar successor: the full 43-row
                # harvest pages at Discord's 25-option cap with engine
                # ◀ Prev / Next ▶ nav (the oracle's PaginatedSelectView
                # posture) — no front-truncation (module docstring ledger).
                page_size=_COG_PAGE_SIZE, windowed=True),
        ),
        actions=(
            PanelActionSpec(
                action_id="routing_enable", label="Enable",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.cog_routing_enable")),
            PanelActionSpec(
                action_id="routing_disable", label="Disable",
                style=ActionStyle.DANGER,
                handler=HandlerRef("setup.cog_routing_disable")),
            PanelActionSpec(
                action_id="routing_back_step", label="↩ Back to step",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.wizard_back_to_step")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("routing_scope",), ("routing_profile",), ("routing_target",),
            ("routing_cog",),
            ("routing_enable", "routing_disable", "routing_back_step"))),)),
        renderer_override=HandlerRef("setup.cog_routing_detail_render"),
        justification=(
            "the shipped cog-routing detail reveals its pickers stepwise "
            "(the oracle opened the target, cog and Enable/Disable picks "
            "as successive ephemeral views — cog_routing._ScopeSelect / "
            "_build_cog_pick_view / _EnableDisableSelect), the target/cog "
            "selects exist only after the prior pick and carry per-pick "
            "dynamic placeholders (the shipped f-string placeholders), "
            "the Enable/Disable pair reveals only after the cog pick "
            "(the oracle's third ephemeral view — declared button faces, "
            "module docstring ledger) and its ↩ Back to step button "
            "rides only the wizard-native path — all outside the static "
            "grammar vocabulary; the override composes the embed and "
            "filters/patches the components (no golden pins it — the "
            "oracle source does)."),
        session_lifecycle=True,
    )


def _ensure_providers() -> None:
    from sb.spec.refs import ProviderRef, is_registered, provider

    if is_registered(ProviderRef(_SCOPE_OPTIONS_PROVIDER)):
        return

    @provider(_SCOPE_OPTIONS_PROVIDER)
    async def scope_options(ctx):
        """cog_routing.SCOPE_OPTIONS, verbatim."""
        picked = _PICKED_SCOPE.get(_key(ctx), "")
        return (
            {"label": "Server default", "value": "guild",
             "description": "Enable / disable a cog server-wide.",
             "emoji": "🌐", "default": picked == "guild"},
            {"label": "Category override", "value": "category",
             "description": ("Override one category; channels inherit "
                             "unless overridden."),
             "emoji": "📁", "default": picked == "category"},
            {"label": "Channel override", "value": "channel",
             "description": "Override one specific channel.",
             "emoji": "📡", "default": picked == "channel"},
        )

    @provider(_PROFILE_OPTIONS_PROVIDER)
    async def profile_options(ctx):
        """_RoutingProfileSelect's options, verbatim caps."""
        del ctx
        return tuple(
            {"label": profile.display_name[:100], "value": profile.slug,
             "description": profile.description[:100]}
            for profile in PROFILES.values())

    @provider(_COG_OPTIONS_PROVIDER)
    async def cog_options(ctx):
        """_cog_options over the operator-visible list — the FULL 43-row
        harvest: the declared ``windowed`` cog select pages it at the
        25-option cap through the kernel selectwindow engine (the
        windowed-select grammar successor; the oracle paginated via
        ``PaginatedSelectView`` — no row is ever front-truncated)."""
        picked = _PICKED_COG.get(_key(ctx), "")
        return tuple(
            _cog_option(name, default=name == picked)
            for name in operator_visible_cogs())


async def _render_cog_routing_detail(spec, ctx):
    import dataclasses

    from sb.domain.setup import wizard_nav
    from sb.kernel.panels.render import render_panel

    guild_id = int(ctx.guild_id or 0)
    user_id = int(getattr(ctx.actor, "user_id", 0) or 0)
    embed = build_cog_routing_embed()

    base = await render_panel(spec, ctx)
    scope = _PICKED_SCOPE.get(_key(ctx), "")
    target = _PICKED_TARGET.get(_key(ctx))
    cog = _PICKED_COG.get(_key(ctx), "")
    from_wizard = wizard_nav.detail_from_wizard(guild_id, user_id)
    components = []
    for c in base.components:
        leaf = c.custom_id.removeprefix(f"{spec.panel_id}.")
        if c.custom_id.startswith("nav:selwin:"):
            # the cog select's engine-injected ◀ Prev / Next ▶ window nav
            # (the only windowed selector on this panel) follows the
            # select's stepwise reveal — hidden until the cog pick opens.
            if not scope or (scope != "guild" and target is None):
                continue
            components.append(c)
            continue
        if leaf == "routing_target":
            if scope not in ("category", "channel"):
                continue    # the picker opens after a scope pick
            # shipped placeholders, verbatim (_CategoryPickSelect /
            # _ChannelPickSelect).
            c = dataclasses.replace(
                c, placeholder=("Pick a category…" if scope == "category"
                                else "Pick a channel…"))
        elif leaf == "routing_cog":
            if not scope:
                continue    # the cog pick opens after a scope pick
            if scope != "guild" and target is None:
                continue    # override scopes need their target first
            # shipped placeholder, verbatim (_build_cog_pick_view) — the
            # windowed engine's " — page p/n" suffix (the shipped
            # SelectWindow byte shape) survives the per-scope patch.
            placeholder = c.placeholder or ""
            suffix = (placeholder[placeholder.rindex(" — page "):]
                      if " — page " in placeholder else "")
            c = dataclasses.replace(
                c, placeholder=f"Pick a cog for {scope} scope…{suffix}")
        elif leaf in ("routing_enable", "routing_disable"):
            if not cog:
                continue    # Enable/Disable opens after the cog pick
                # (the oracle's third ephemeral view)
        elif c.custom_id == "cog_routing_section_profile":
            pass            # the batch picker is always live
        elif leaf == "routing_back_step" and not from_wizard:
            continue        # the shipped wizard-native-only injection
        components.append(c)
    return dataclasses.replace(base, embed=embed,
                               components=tuple(components))


# --- handlers ------------------------------------------------------------------------------------

#: the folded-panel stale-card guard (the oracle's stepwise ephemeral
#: views made these states unreachable — the cleanup footer-copy
#: precedent; the embed's How-to-use field is the instruction).
_PICK_SCOPE_FIRST = "Pick a scope first — see **How to use** above."


async def _stage_cog_routing(req, *, scope_kind: str, scope_id: int | None,
                             scope_name: str, cog_name: str,
                             enabled: bool) -> Reply:
    """cog_routing._stage_cog_routing, ported onto the K9 spine (gated
    on the ported can-apply ladder — the channels-flow additive
    fence)."""
    from sb.domain.setup import section_card, wizard
    from sb.domain.setup.wizard import _refresh_own_panel

    guild_id = int(req.guild_id or 0)
    if not guild_id:
        # shipped copy, verbatim.
        return Reply(BLOCKED, "This can only be used in a server.")
    if not await section_card._gated_card(req):
        return Reply(BLOCKED, section_card.GATE_MSG_CARD)
    op = _routing_op(scope_kind=scope_kind, scope_id=scope_id,
                     scope_name=scope_name, cog_name=cog_name,
                     enabled=enabled)
    label = op.label_body
    try:
        await section_card.stage_custom(guild_id, SLUG, op)
    except Exception:  # noqa: BLE001 — the shipped error copy answers
        logger.exception("cog_routing: setup_draft.append failed")
        # shipped copy, verbatim.
        return Reply(BLOCKED,
                     "Could not stage the routing policy — see logs.")
    await section_card.mark_step_in_progress(req, SLUG)
    try:
        pending = await wizard.staged_ops_count(guild_id)
    except Exception:  # noqa: BLE001 — the shipped count soft-fail
        logger.exception("cog_routing: setup_draft.count failed")
        pending = 0
    await _refresh_own_panel(req, {})
    # shipped confirmation, verbatim (the double space included).
    return Reply(SUCCESS,
                 f"✅ Staged for Final review: `{label}`.  "
                 f"Pending operations: **{pending}**.")


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.cog_routing_scope_pick")):
        return

    @handler("setup.open_section_cog_routing")
    async def open_section_cog_routing(req) -> Reply | None:
        """The hub's Cog-routing section button — gate exactly like the
        shipped hub button, land on the section card (cog_routing.run →
        section_card.show), record the step marker."""
        from sb.domain.setup import section_card, wizard
        from sb.domain.setup.wizard import _open

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, wizard.GATE_MSG_WIZARD)
        await _open(req, section_card.card_panel_id(SLUG))
        await section_card.mark_step_in_progress(req, SLUG)
        return None

    @handler("setup.cog_routing_scope_pick")
    async def cog_routing_scope_pick(req) -> Reply | None:
        """_ScopeSelect.callback: stash the scope; the next control
        (cog select for guild, target picker for overrides) reveals on
        the refreshed card (the oracle's second ephemeral view)."""
        from sb.domain.setup.wizard import _open, _refresh_own_panel

        values = tuple(req.args.get("values", ()) or ())
        scope = str(values[0]) if values else ""
        if scope not in ("guild", "category", "channel"):
            return Reply(BLOCKED, f"Unknown scope `{scope}`.")
        _PICKED_SCOPE[_key(req)] = scope
        _PICKED_TARGET.pop(_key(req), None)
        _PICKED_COG.pop(_key(req), None)
        if not await _refresh_own_panel(req, {}):
            await _open(req, COG_ROUTING_DETAIL_PANEL_ID)
        return None

    @handler("setup.cog_routing_target_pick")
    async def cog_routing_target_pick(req) -> Reply | None:
        """_CategoryPickSelect / _ChannelPickSelect.callback: stash the
        override target; the cog select reveals with its per-scope
        placeholder."""
        from sb.domain.setup.channels import _channel_name
        from sb.domain.setup.wizard import _open, _refresh_own_panel

        values = tuple(req.args.get("values", ()) or ())
        raw = str(values[0]) if values else ""
        if not raw.lstrip("-").isdigit():
            return Reply(BLOCKED, "No channel picked.")
        if _PICKED_SCOPE.get(_key(req)) not in ("category", "channel"):
            # a stale card (module docstring ledger).
            return Reply(BLOCKED, _PICK_SCOPE_FIRST)
        target_id = int(raw)
        guild_id = int(req.guild_id or 0)
        resolved = await _channel_name(guild_id, target_id)
        _PICKED_TARGET[_key(req)] = (target_id, resolved or str(target_id))
        _PICKED_COG.pop(_key(req), None)
        if not await _refresh_own_panel(req, {}):
            await _open(req, COG_ROUTING_DETAIL_PANEL_ID)
        return None

    @handler("setup.cog_routing_cog_pick")
    async def cog_routing_cog_pick(req) -> Reply | None:
        """The cog pick (_build_cog_pick_view._on_cog_picked): stash the
        cog; Enable/Disable reveals with its per-cog placeholder."""
        from sb.domain.setup.wizard import _open, _refresh_own_panel

        values = tuple(req.args.get("values", ()) or ())
        cog = str(values[0]) if values else ""
        if not cog:
            # shipped copy, verbatim (_on_cog_picked's empty branch).
            return Reply(BLOCKED, "No visible subsystems registered.")
        if cog not in operator_visible_cogs():
            return Reply(BLOCKED, f"Unknown cog `{cog}`.")
        if not _PICKED_SCOPE.get(_key(req)):
            # a stale card (module docstring ledger).
            return Reply(BLOCKED, _PICK_SCOPE_FIRST)
        _PICKED_COG[_key(req)] = cog
        if not await _refresh_own_panel(req, {}):
            await _open(req, COG_ROUTING_DETAIL_PANEL_ID)
        return None

    async def _flag_click(req, *, enabled: bool) -> Reply:
        """_EnableDisableSelect.callback → one staged
        ``set_cog_routing`` op for the picked (scope, target, cog) —
        the Enable/Disable pick rides the declared button pair (module
        docstring ledger)."""
        scope = _PICKED_SCOPE.get(_key(req), "")
        cog = _PICKED_COG.get(_key(req), "")
        if not scope or not cog:
            return Reply(BLOCKED, _PICK_SCOPE_FIRST)
        if scope == "guild":
            # the shipped guild-scope spelling (scope_id=None,
            # scope_name="guild" — _ScopeSelect's guild branch).
            return await _stage_cog_routing(
                req, scope_kind="guild", scope_id=None, scope_name="guild",
                cog_name=cog, enabled=enabled)
        target = _PICKED_TARGET.get(_key(req))
        if target is None:
            return Reply(BLOCKED, _PICK_SCOPE_FIRST)
        target_id, target_name = target
        return await _stage_cog_routing(
            req, scope_kind=scope, scope_id=target_id,
            scope_name=target_name, cog_name=cog, enabled=enabled)

    @handler("setup.cog_routing_enable")
    async def cog_routing_enable(req) -> Reply:
        return await _flag_click(req, enabled=True)

    @handler("setup.cog_routing_disable")
    async def cog_routing_disable(req) -> Reply:
        return await _flag_click(req, enabled=False)

    @handler("setup.cog_routing_profile_pick")
    async def cog_routing_profile_pick(req) -> Reply:
        """_RoutingProfileSelect.callback, ported: stage every op the
        profile's builder returns (per-op isolation, the shipped
        posture), answer the shipped staged/pending summary."""
        from sb.domain.setup import section_card, wizard
        from sb.domain.setup.wizard import _refresh_own_panel

        guild_id = int(req.guild_id or 0)
        if not guild_id:
            # shipped copy, verbatim.
            return Reply(BLOCKED, "This can only be used in a server.")
        values = tuple(req.args.get("values", ()) or ())
        slug = str(values[0]) if values else ""
        profile = get_routing_profile(slug)
        if profile is None:
            # shipped copy, verbatim.
            return Reply(BLOCKED, f"Unknown cog routing profile `{slug}`.")
        if not await section_card._gated_card(req):
            return Reply(BLOCKED, section_card.GATE_MSG_CARD)
        try:
            ops = await routing_profile_ops(profile, guild_id)
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception("cog_routing: apply_profile failed (slug=%s)",
                             slug)
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "Could not build the routing profile — see logs.")
        if not ops:
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         f"Profile `{slug}` produced no operations.")
        staged = 0
        for op in ops:
            try:
                await section_card.stage_custom(guild_id, SLUG, op)
                staged += 1
            except Exception:  # noqa: BLE001 — per-op isolation (shipped)
                logger.exception(
                    "cog_routing: profile append failed (slug=%s, target=%s)",
                    slug, op.payload.get("scope_id"))
        await section_card.mark_step_in_progress(req, SLUG)
        try:
            pending = await wizard.staged_ops_count(guild_id)
        except Exception:  # noqa: BLE001 — the shipped count soft-fail
            logger.exception(
                "cog_routing: setup_draft.count failed (profile)")
            pending = 0
        await _refresh_own_panel(req, {})
        word = "operation" if staged == 1 else "operations"
        # shipped summary, verbatim.
        return Reply(SUCCESS,
                     f"✅ Staged **{staged} {word}** for profile "
                     f"`{profile.display_name}`. Pending operations: "
                     f"**{pending}**.")


# --- registration ------------------------------------------------------------------------------------

def _register_panels() -> None:
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    if not is_registered(HandlerRef("setup.cog_routing_detail_render")):
        handler("setup.cog_routing_detail_render")(_render_cog_routing_detail)
    if not is_registered(PanelRef(COG_ROUTING_DETAIL_PANEL_ID)):
        panel(COG_ROUTING_DETAIL_PANEL_ID)(cog_routing_detail_spec)


def _register_section() -> None:
    from sb.domain.setup import section_card

    # NO recommended builder (cog_routing.run:
    # recommended_ops_builder=None — "routing changes are server-wide
    # and can silently break the bot's behaviour if misapplied").
    section_card.register_customize_panel(SLUG, COG_ROUTING_DETAIL_PANEL_ID)
    section_card.register_section_card(SLUG, detected_state=_DETECTED_STATE)


_ensure_providers()
_register()
_register_panels()
_register_section()
_register_set_cog_routing_op_kind()


def ensure_setup_cog_routing_refs() -> None:
    _ensure_providers()
    _register()
    _register_panels()
    _register_section()
    _register_set_cog_routing_op_kind()

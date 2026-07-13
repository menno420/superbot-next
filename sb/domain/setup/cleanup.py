"""The CLEANUP-INHERITANCE section flow (the settings-write slice),
ported from the oracle (menno420/superbot, read from the LOCAL oracle
clone: views/setup/sections/cleanup.py + services/cleanup_levels.py +
services/cleanup_profiles.py + utils/channel_classify.py's consumed
tag subset):

* the LEVEL VOCABULARY (``LEVELS``, data verbatim): Off / Light /
  Standard / Strict → the three ``cleanup_policies`` column values,
  plus the ``cleanup_scope_id`` write-side scope-id convention (a
  guild-default row keys at ``guild_id``, never 0 — the
  silent-no-op-bug helper, carried verbatim);
* the SCOPE WALKER (``_ScopeSelect`` → per-scope level pick, flow
  verbatim): Server default / Category override / Channel override;
  a guild pick reveals the level select directly, category/channel
  picks reveal the native channel picker first; every level pick
  stages ONE ``set_cleanup_policy`` op and answers the shipped
  staged/pending confirmation;
* the PROFILE BATCH PICKER (``_ProfileSelect`` + the six-profile
  catalogue, copy verbatim): off / light / standard / strict uniform
  guild-scope profiles plus ``silent_bot`` (Strict on detected
  bot/command channels, Light elsewhere) and ``moderation_safe``
  (Standard everywhere, Off on detected mod/admin/staff channels) —
  detection rides the carried ``classify_channel_name`` tag subset;
* APPLY RECOMMENDED (``_recommended_cleanup_ops``, semantics
  verbatim): Light at guild scope — "delete invalid commands after
  10s and leave failed-command messages alone";
* the K9→K7 REGISTRATION: the ``set_cleanup_policy`` op kind binds
  onto the audited K7 ``governance.set_cleanup`` op (policy row +
  governance audit row in one transaction — the oracle
  ``governance.writes.set_cleanup_policy_for_scope`` twin); the level
  → column translation happens at STAGE time (the oracle Final-Review
  dispatcher's ``columns_for_level`` read), and the payload carries
  the level name + scope label alongside for the review renderer.

Kernel-idiom divergences, ledgered (the section_card.py doctrine):

* ONE native channel picker serves both the category and the channel
  scope (placeholder patched per scope) — the grammar's CHANNEL
  selector carries no channel-type filter (the oracle's
  ``channel_types=[category]`` typed picker is a flagged follow-up);
* profile channel detection walks the advisor's installed channel
  index (plan._channel_index — the guild-snapshot seam the channels
  flow reads); a headless runtime detects nothing and the profiles
  degrade to their guild-scope fallback rows (silent_bot's own
  documented fallback);
* ``classify_channel_name`` is carried as the CONSUMED tag subset
  (likely_bot_cmd / likely_mod / likely_admin / likely_mod_log —
  patterns verbatim; the preset_select carried-slug precedent);
* profile rows ride ``stage_custom`` so the label carries the
  ``[cleanup] `` provenance prefix + the shipped
  ``[profile:{slug}] …`` tail (the oracle appended them
  section_slug-less — op_kinds fallback matched anyway; provenance
  here is strictly more precise);
* staged K9 rows carry no oracle metadata dict — the final_review.py
  ledger note's class.

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
    "CLEANUP_DETAIL_PANEL_ID",
    "LEVELS",
    "PROFILES",
    "CleanupProfile",
    "build_cleanup_embed",
    "classify_channel_name",
    "cleanup_detail_spec",
    "cleanup_scope_id",
    "ensure_setup_cleanup_refs",
    "get_profile",
    "recommended_cleanup_ops",
    "reset_cleanup_state_for_tests",
]

logger = logging.getLogger("sb.domain.setup")

SLUG = "cleanup"

CLEANUP_DETAIL_PANEL_ID = "setup.cleanup_detail"

_SCOPE_OPTIONS_PROVIDER = "setup.cleanup_scope_options"
_PROFILE_OPTIONS_PROVIDER = "setup.cleanup_profile_options"
_LEVEL_OPTIONS_PROVIDER = "setup.cleanup_level_options"

#: the shipped card copy, verbatim (cleanup.run's ``detected``).
_DETECTED_STATE = ("Resolver walks thread → channel → category → server → "
                   "default.")


# --- the level vocabulary (services/cleanup_levels.py, data verbatim) ------------------------

LEVELS: dict[str, dict] = {
    "Off": {
        "delete_invalid_commands": False,
        "delete_failed_commands": False,
        "delete_after_seconds": 0,
    },
    "Light": {
        "delete_invalid_commands": True,
        "delete_failed_commands": False,
        "delete_after_seconds": 10,
    },
    "Standard": {
        "delete_invalid_commands": True,
        "delete_failed_commands": True,
        "delete_after_seconds": 5,
    },
    "Strict": {
        "delete_invalid_commands": True,
        "delete_failed_commands": True,
        "delete_after_seconds": 2,
    },
}


def cleanup_scope_id(scope_type: str, guild_id: int,
                     scope_id: int | None) -> int:
    """cleanup_levels.cleanup_scope_id, verbatim: a guild-default
    policy MUST key at ``guild_id``, never 0 (the resolver looks a
    guild-scope row up at ``scope_id == guild_id`` — the
    silent-no-op bug this helper exists to prevent); category/channel
    rows key by their snowflake."""
    if scope_type == "guild":
        return int(guild_id)
    if scope_id is None:
        raise ValueError(f"{scope_type} cleanup scope requires a scope_id")
    return int(scope_id)


# --- the consumed channel-classifier subset (utils/channel_classify.py, patterns verbatim) ---

_NAME_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "likely_mod_log": (
        re.compile(r"\bmod[-_]?logs?\b"),
        re.compile(r"\bmoderation[-_]?logs?\b"),
        re.compile(r"\bstaff[-_]?logs?\b"),
    ),
    "likely_bot_cmd": (
        re.compile(r"\bbot[-_]?(?:cmd|cmds|commands?|spam)\b"),
        re.compile(r"\bcmds?\b"),
        re.compile(r"\bcommands?\b"),
    ),
    "likely_admin": (
        re.compile(r"\badmin\b"),
        re.compile(r"\bowner\b"),
        re.compile(r"\bstaff[-_]?only\b"),
    ),
    "likely_mod": (
        re.compile(r"\bmods?\b"),
        re.compile(r"\bmoderation\b"),
        re.compile(r"\bstaff\b"),
    ),
}


def classify_channel_name(name: str) -> tuple[str, ...]:
    """channel_classify.classify_channel_name over the consumed tag
    subset (module docstring ledger) — sorted for deterministic
    output, the shipped contract."""
    if not name:
        return ()
    lowered = name.lower()
    return tuple(sorted(
        tag for tag, patterns in _NAME_PATTERNS.items()
        if any(p.search(lowered) for p in patterns)))


def _is_bot_channel(name: str) -> bool:
    return "likely_bot_cmd" in classify_channel_name(name or "")


def _is_moderation_channel(name: str) -> bool:
    tags = classify_channel_name(name or "")
    return bool({"likely_mod", "likely_admin", "likely_mod_log"} & set(tags))


# --- staged-op builders ------------------------------------------------------------------------

def _policy_op(*, scope_type: str, scope_id: int, scope_name: str,
               level: str, label_body: str | None = None):
    """One ``set_cleanup_policy`` StagedSectionOp: the K7
    ``governance.set_cleanup`` params (scope_type/scope_id + the three
    columns_for_level values, translated at stage time) plus the
    review-renderer ride-alongs (level / target_name; the extra keys
    ride ABOVE the op's declared minimum — the stage_accepted
    precedent). ``name`` keys the replace-on-conflict slot per scope
    (a re-picked level replaces, never duplicates — the oracle
    append's slot semantics)."""
    from sb.domain.setup.section_card import StagedSectionOp

    columns = LEVELS[level]
    return StagedSectionOp(
        op_kind="set_cleanup_policy", subsystem="cleanup",
        payload={"name": f"{scope_type}:{scope_id}",
                 "scope_type": scope_type, "scope_id": int(scope_id),
                 "delete_invalid_commands":
                     bool(columns["delete_invalid_commands"]),
                 "delete_failed_commands":
                     bool(columns["delete_failed_commands"]),
                 "delete_after_seconds":
                     int(columns["delete_after_seconds"]),
                 "level": level, "target_name": scope_name},
        label_body=(label_body
                    or f"cleanup.{scope_type}({scope_name}) = {level}"))


_SET_CLEANUP_OP_KIND = "set_cleanup_policy"


def _register_set_cleanup_op_kind() -> None:
    """Bind the ``set_cleanup_policy`` op kind onto the audited K7
    ``governance.set_cleanup`` op (the preset_select ``set_setting`` →
    ``settings.set_scalar`` precedent): policy row + governance audit
    row in one transaction — the oracle Final-Review dispatcher's
    ``governance.writes.set_cleanup_policy_for_scope`` route."""
    from sb.kernel.draft.registry import OP_KINDS, OpKindBinding
    from sb.spec.events import FieldSpec
    from sb.spec.refs import WorkflowRef

    binding = OpKindBinding(
        op_kind=_SET_CLEANUP_OP_KIND,
        workflow_ref=WorkflowRef("governance.set_cleanup"),
        payload_schema=(FieldSpec("scope_type", "str"),
                        FieldSpec("scope_id", "int"),
                        FieldSpec("delete_invalid_commands", "bool"),
                        FieldSpec("delete_failed_commands", "bool"),
                        FieldSpec("delete_after_seconds", "int")),
        is_resource_create=False)
    try:
        OP_KINDS.register(binding)
    except ValueError as exc:
        if "bound twice" not in str(exc):
            raise


# --- the profile catalogue (services/cleanup_profiles.py, copy verbatim) -----------------------

@dataclass(frozen=True)
class CleanupProfile:
    """One named cleanup bundle (cleanup_profiles.CleanupProfile —
    the builder rides the (id, name) channel listing)."""

    slug: str
    display_name: str
    description: str
    uniform_level: str | None = None    # guild-scope-only profiles
    kind: str = "uniform"               # uniform | silent_bot | moderation_safe


PROFILES: dict[str, CleanupProfile] = {
    "off": CleanupProfile(
        slug="off", display_name="Off",
        description=("Disable cleanup everywhere. The server keeps every "
                     "command prompt."),
        uniform_level="Off"),
    "light": CleanupProfile(
        slug="light", display_name="Light",
        description=("Delete invalid command prompts after 10s. Failed "
                     "commands stay."),
        uniform_level="Light"),
    "standard": CleanupProfile(
        slug="standard", display_name="Standard",
        description="Delete invalid and failed command prompts after 5s.",
        uniform_level="Standard"),
    "strict": CleanupProfile(
        slug="strict", display_name="Strict",
        description=("Aggressively delete invalid and failed prompts "
                     "after 2s."),
        uniform_level="Strict"),
    "silent_bot": CleanupProfile(
        slug="silent_bot", display_name="Silent bot channel",
        description=(
            "Strict cleanup on detected bot/command channels, Light "
            "everywhere else. Keeps command spam out of bot channels "
            "without hiding evidence elsewhere."),
        kind="silent_bot"),
    "moderation_safe": CleanupProfile(
        slug="moderation_safe", display_name="Moderation safe",
        description=(
            "Standard cleanup everywhere, but Off on detected mod / "
            "admin / staff channels so moderation context and evidence "
            "are preserved."),
        kind="moderation_safe"),
}


def get_profile(slug: str) -> CleanupProfile | None:
    return PROFILES.get(slug)


async def _guild_channels(guild_id: int):
    """The profile builders' channel listing off the advisor's channel
    index (module docstring ledger — the channels-flow seam)."""
    from sb.domain.setup import plan

    if plan._channel_index is None:
        return ()
    try:
        return tuple(await plan._channel_index(int(guild_id)) or ())
    except Exception:  # noqa: BLE001 — headless ⇒ guild-scope fallback rows
        logger.debug("cleanup: channel index read failed", exc_info=True)
        return ()


async def _guild_name(guild_id: int) -> str:
    try:
        from sb.domain.utility.service import guild_directory

        info = await guild_directory().guild_info(int(guild_id))
        return str(info.name)
    except Exception:  # noqa: BLE001 — headless directory ⇒ the slug answers
        return "guild"


async def profile_ops(profile: CleanupProfile, guild_id: int) -> list:
    """cleanup_profiles' builders, ported (deterministic, side-effect
    free — same guild + same channel set → same op order): a
    guild-scope row first, then the detected per-channel overrides."""
    guild_name = await _guild_name(guild_id)
    label = "[profile:{slug}] cleanup.{kind}({name}) = {level}"

    def _guild_row(level: str):
        return _policy_op(
            scope_type="guild", scope_id=int(guild_id),
            scope_name=guild_name, level=level,
            label_body=label.format(slug=profile.slug, kind="guild",
                                    name=guild_name, level=level))

    def _channel_row(channel, level: str):
        return _policy_op(
            scope_type="channel", scope_id=int(channel.id),
            scope_name=str(channel.name), level=level,
            label_body=label.format(slug=profile.slug, kind="channel",
                                    name=channel.name, level=level))

    if profile.kind == "uniform":
        return [_guild_row(str(profile.uniform_level))]
    channels = await _guild_channels(guild_id)
    if profile.kind == "silent_bot":
        ops = [_guild_row("Light")]
        ops.extend(_channel_row(c, "Strict") for c in channels
                   if _is_bot_channel(str(c.name)))
        return ops
    if profile.kind == "moderation_safe":
        ops = [_guild_row("Standard")]
        ops.extend(_channel_row(c, "Off") for c in channels
                   if _is_moderation_channel(str(c.name)))
        return ops
    return []


async def recommended_cleanup_ops(guild_id: int) -> list:
    """Default cleanup recommendation: Light at guild scope
    (cleanup._recommended_cleanup_ops — "a safe baseline for most
    servers")."""
    name = await _guild_name(int(guild_id))
    return [_policy_op(scope_type="guild", scope_id=int(guild_id),
                       scope_name=name, level="Light")]


# --- the entry embed (build_cleanup_embed, bytes verbatim) --------------------------------------

def build_cleanup_embed():
    from sb.kernel.panels.render import RenderedEmbed

    return RenderedEmbed(
        title="🧹 Cleanup inheritance",
        description=(
            "Configure cleanup behaviour at three scopes.  The resolver "
            "walks **thread → channel → category → server → default**, so "
            "channel overrides win over category overrides which win "
            "over the server default.  Each pick stages a "
            "`set_cleanup_policy` operation — Final review applies "
            "them all in order."),
        fields=(
            ("Levels",
             ("• **Off** — disabled (after=0s)\n"
              "• **Light** — delete invalid commands only (after=10s)\n"
              "• **Standard** — delete invalid + failed (after=5s)\n"
              "• **Strict** — delete invalid + failed (after=2s)"),
             False),
        ),
        footer="Pick a scope below, then pick a level for that scope.",
        style_token="blurple")


# --- flow state ----------------------------------------------------------------------------------

#: guild:user → the picked scope kind ("guild" | "category" | "channel").
_PICKED_SCOPE: dict[str, str] = {}
#: guild:user → the picked override target (id, name).
_PICKED_TARGET: dict[str, tuple[int, str]] = {}


def _key(req_or_ctx) -> str:
    return (f"{int(req_or_ctx.guild_id or 0)}:"
            f"{int(getattr(req_or_ctx.actor, 'user_id', 0) or 0)}")


def reset_cleanup_state_for_tests() -> None:
    _PICKED_SCOPE.clear()
    _PICKED_TARGET.clear()


# --- the detail panel ------------------------------------------------------------------------------

def cleanup_detail_spec():
    """CleanupSectionView + the per-scope pick sub-views folded onto one
    panel: the scope select (row 0), the profile batch picker (row 1,
    the shipped ``cleanup_section_profile`` custom_id), the
    state-dependent native target picker (row 2 — category/channel
    scopes only) and level select (row 3), and the wizard-origin
    ↩ Back to step button (row 4)."""
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        NavigationSpec, PageSpec, PanelActionSpec, PanelSpec, SelectorKind,
        SelectorSpec,
    )
    from sb.spec.refs import HandlerRef, ProviderRef

    return PanelSpec(
        panel_id=CLEANUP_DETAIL_PANEL_ID,
        subsystem="setup",
        title="🧹 Cleanup inheritance",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="cleanup_scope", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.cleanup_scope_pick"),
                options_source=ProviderRef(_SCOPE_OPTIONS_PROVIDER),
                placeholder="Pick a scope to set cleanup for…"),
            SelectorSpec(
                selector_id="cleanup_profile", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.cleanup_profile_pick"),
                options_source=ProviderRef(_PROFILE_OPTIONS_PROVIDER),
                placeholder="Apply a cleanup profile (batch action)…",
                custom_id_override="cleanup_section_profile"),
            SelectorSpec(
                selector_id="cleanup_target", kind=SelectorKind.CHANNEL,
                on_select=HandlerRef("setup.cleanup_target_pick"),
                placeholder="Pick a channel…"),
            SelectorSpec(
                selector_id="cleanup_level", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.cleanup_level_pick"),
                options_source=ProviderRef(_LEVEL_OPTIONS_PROVIDER),
                placeholder="Pick the server-wide level…"),
        ),
        actions=(
            PanelActionSpec(
                action_id="cleanup_back_step", label="↩ Back to step",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.wizard_back_to_step")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("cleanup_scope",), ("cleanup_profile",), ("cleanup_target",),
            ("cleanup_level",), ("cleanup_back_step",))),)),
        renderer_override=HandlerRef("setup.cleanup_detail_render"),
        justification=(
            "the shipped cleanup detail reveals its pickers stepwise (the "
            "oracle opened each scope's level select as a second ephemeral "
            "view — cleanup._ScopeSelect.callback), the target picker and "
            "level select exist only after the prior pick and carry "
            "per-pick dynamic placeholders (cleanup._CategoryLevelSelect / "
            "_ChannelLevelSelect placeholder f-strings), and its ↩ Back "
            "to step button rides only the wizard-native path — all "
            "outside the static grammar vocabulary; the override composes "
            "the embed and filters/patches the components (no golden pins "
            "it — the oracle source does)."),
        session_lifecycle=True,
    )


def _ensure_providers() -> None:
    from sb.spec.refs import ProviderRef, is_registered, provider

    if is_registered(ProviderRef(_SCOPE_OPTIONS_PROVIDER)):
        return

    @provider(_SCOPE_OPTIONS_PROVIDER)
    async def scope_options(ctx):
        """cleanup.SCOPE_OPTIONS, verbatim."""
        picked = _PICKED_SCOPE.get(_key(ctx), "")
        return (
            {"label": "Server default", "value": "guild",
             "description": ("Cleanup level for every channel without an "
                             "override."),
             "emoji": "🌐", "default": picked == "guild"},
            {"label": "Category override", "value": "category",
             "description": ("Override one category — channels in it "
                             "inherit unless overridden."),
             "emoji": "📁", "default": picked == "category"},
            {"label": "Channel override", "value": "channel",
             "description": "Override one specific channel.",
             "emoji": "📡", "default": picked == "channel"},
        )

    @provider(_PROFILE_OPTIONS_PROVIDER)
    async def profile_options(ctx):
        """cleanup._ProfileSelect's options, verbatim caps."""
        del ctx
        return tuple(
            {"label": profile.display_name, "value": profile.slug,
             "description": profile.description[:100]}
            for profile in PROFILES.values())

    @provider(_LEVEL_OPTIONS_PROVIDER)
    async def level_options(ctx):
        """cleanup._level_options, verbatim description bytes."""
        del ctx
        return tuple(
            {"label": name, "value": name,
             "description": (
                 f"after={values['delete_after_seconds']}s · "
                 f"invalid="
                 f"{'yes' if values['delete_invalid_commands'] else 'no'} · "
                 f"failed="
                 f"{'yes' if values['delete_failed_commands'] else 'no'}")}
            for name, values in LEVELS.items())


async def _render_cleanup_detail(spec, ctx):
    import dataclasses

    from sb.domain.setup import wizard_nav
    from sb.kernel.panels.render import render_panel

    guild_id = int(ctx.guild_id or 0)
    user_id = int(getattr(ctx.actor, "user_id", 0) or 0)
    embed = build_cleanup_embed()

    base = await render_panel(spec, ctx)
    scope = _PICKED_SCOPE.get(_key(ctx), "")
    target = _PICKED_TARGET.get(_key(ctx))
    from_wizard = wizard_nav.detail_from_wizard(guild_id, user_id)
    components = []
    for c in base.components:
        leaf = c.custom_id.removeprefix(f"{spec.panel_id}.")
        if leaf == "cleanup_target":
            if scope not in ("category", "channel"):
                continue    # the picker opens after a scope pick
            c = dataclasses.replace(
                c, placeholder=("Pick a category…" if scope == "category"
                                else "Pick a channel…"))
        elif leaf == "cleanup_level":
            if not scope:
                continue    # the level select opens after a scope pick
            if scope == "guild":
                # shipped placeholder, verbatim (_GuildLevelSelect).
                c = dataclasses.replace(
                    c, placeholder="Pick the server-wide level…")
            elif target is None:
                continue    # override scopes need their target first
            elif scope == "category":
                # shipped placeholder, verbatim (_CategoryLevelSelect).
                c = dataclasses.replace(
                    c, placeholder=f"Level for category {target[1]}…")
            else:
                # shipped placeholder, verbatim (_ChannelLevelSelect).
                c = dataclasses.replace(
                    c, placeholder=f"Level for channel #{target[1]}…")
        elif c.custom_id == "cleanup_section_profile":
            pass            # the batch picker is always live
        elif leaf == "cleanup_back_step" and not from_wizard:
            continue        # the shipped wizard-native-only injection
        components.append(c)
    return dataclasses.replace(base, embed=embed,
                               components=tuple(components))


# --- handlers ---------------------------------------------------------------------------------------

async def _stage_cleanup_policy(req, *, scope_kind: str,
                                scope_id: int | None, scope_name: str,
                                level: str) -> Reply:
    """cleanup._stage_cleanup_policy, ported onto the K9 spine (gated
    on the ported can-apply ladder — the channels-flow additive
    fence)."""
    from sb.domain.setup import section_card, wizard
    from sb.domain.setup.wizard import _refresh_own_panel

    guild_id = int(req.guild_id or 0)
    if not guild_id:
        # shipped copy, verbatim.
        return Reply(BLOCKED, "This can only be used in a server.")
    if level not in LEVELS:
        # shipped copy, verbatim.
        return Reply(BLOCKED, f"Unknown level `{level}`.")
    if not await section_card._gated_card(req):
        return Reply(BLOCKED, section_card.GATE_MSG_CARD)
    _register_set_cleanup_op_kind()
    label = f"cleanup.{scope_kind}({scope_name}) = {level}"
    try:
        await section_card.stage_custom(guild_id, SLUG, _policy_op(
            scope_type=scope_kind,
            scope_id=cleanup_scope_id(scope_kind, guild_id, scope_id),
            scope_name=scope_name, level=level))
    except Exception:  # noqa: BLE001 — the shipped error copy answers
        logger.exception("cleanup: setup_draft.append failed")
        # shipped copy, verbatim.
        return Reply(BLOCKED,
                     "Could not stage the cleanup policy — see logs.")
    await section_card.mark_step_in_progress(req, SLUG)
    try:
        pending = await wizard.staged_ops_count(guild_id)
    except Exception:  # noqa: BLE001 — the shipped count soft-fail
        logger.exception("cleanup: setup_draft.count failed")
        pending = 0
    await _refresh_own_panel(req, {})
    # shipped confirmation, verbatim.
    return Reply(SUCCESS,
                 f"✅ Staged for Final review: `{label}`.  "
                 f"Pending operations: **{pending}**.")


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.cleanup_scope_pick")):
        return

    @handler("setup.open_section_cleanup")
    async def open_section_cleanup(req) -> Reply | None:
        """The hub's Cleanup section button — gate exactly like the
        shipped hub button, land on the section card (cleanup.run →
        section_card.show), record the step marker."""
        from sb.domain.setup import section_card, wizard
        from sb.domain.setup.wizard import _open

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, wizard.GATE_MSG_WIZARD)
        await _open(req, section_card.card_panel_id(SLUG))
        await section_card.mark_step_in_progress(req, SLUG)
        return None

    @handler("setup.cleanup_scope_pick")
    async def cleanup_scope_pick(req) -> Reply | None:
        """_ScopeSelect.callback: stash the scope; the next control
        (level select for guild, target picker for overrides) reveals
        on the refreshed card (the oracle's second ephemeral view)."""
        from sb.domain.setup.wizard import _open, _refresh_own_panel

        values = tuple(req.args.get("values", ()) or ())
        scope = str(values[0]) if values else ""
        if scope not in ("guild", "category", "channel"):
            return Reply(BLOCKED, f"Unknown scope `{scope}`.")
        _PICKED_SCOPE[_key(req)] = scope
        _PICKED_TARGET.pop(_key(req), None)
        if not await _refresh_own_panel(req, {}):
            await _open(req, CLEANUP_DETAIL_PANEL_ID)
        return None

    @handler("setup.cleanup_target_pick")
    async def cleanup_target_pick(req) -> Reply | None:
        """_CategoryPickSelect / _ChannelPickSelect.callback: stash the
        override target; the level select reveals with its per-target
        placeholder."""
        from sb.domain.setup.channels import _channel_name
        from sb.domain.setup.wizard import _open, _refresh_own_panel

        values = tuple(req.args.get("values", ()) or ())
        raw = str(values[0]) if values else ""
        if not raw.lstrip("-").isdigit():
            return Reply(BLOCKED, "No channel picked.")
        if _PICKED_SCOPE.get(_key(req)) not in ("category", "channel"):
            # a stale card — the entry footer's instruction answers.
            return Reply(BLOCKED,
                         "Pick a scope below, then pick a level for that "
                         "scope.")
        target_id = int(raw)
        guild_id = int(req.guild_id or 0)
        resolved = await _channel_name(guild_id, target_id)
        _PICKED_TARGET[_key(req)] = (target_id, resolved or str(target_id))
        if not await _refresh_own_panel(req, {}):
            await _open(req, CLEANUP_DETAIL_PANEL_ID)
        return None

    @handler("setup.cleanup_level_pick")
    async def cleanup_level_pick(req) -> Reply:
        """The per-scope level pick → one staged ``set_cleanup_policy``
        (the three oracle level selects folded on the picked scope)."""
        values = tuple(req.args.get("values", ()) or ())
        level = str(values[0]) if values else ""
        scope = _PICKED_SCOPE.get(_key(req), "")
        if not scope:
            return Reply(BLOCKED,
                         "Pick a scope below, then pick a level for that "
                         "scope.")
        if scope == "guild":
            # the shipped guild-scope spelling (scope_name="guild").
            return await _stage_cleanup_policy(
                req, scope_kind="guild", scope_id=None, scope_name="guild",
                level=level)
        target = _PICKED_TARGET.get(_key(req))
        if target is None:
            return Reply(BLOCKED,
                         "Pick a scope below, then pick a level for that "
                         "scope.")
        target_id, target_name = target
        scope_name = (target_name if scope == "category"
                      else f"#{target_name}")
        return await _stage_cleanup_policy(
            req, scope_kind=scope, scope_id=target_id,
            scope_name=scope_name, level=level)

    @handler("setup.cleanup_profile_pick")
    async def cleanup_profile_pick(req) -> Reply:
        """_ProfileSelect.callback, ported: stage every op the profile's
        builder returns (per-op isolation, the shipped posture), answer
        the shipped staged/pending summary."""
        from sb.domain.setup import section_card, wizard
        from sb.domain.setup.wizard import _refresh_own_panel

        guild_id = int(req.guild_id or 0)
        if not guild_id:
            # shipped copy, verbatim.
            return Reply(BLOCKED, "This can only be used in a server.")
        values = tuple(req.args.get("values", ()) or ())
        slug = str(values[0]) if values else ""
        profile = get_profile(slug)
        if profile is None:
            # shipped copy, verbatim.
            return Reply(BLOCKED, f"Unknown cleanup profile `{slug}`.")
        if not await section_card._gated_card(req):
            return Reply(BLOCKED, section_card.GATE_MSG_CARD)
        _register_set_cleanup_op_kind()
        try:
            ops = await profile_ops(profile, guild_id)
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception("cleanup: apply_profile failed (slug=%s)", slug)
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "Could not build the cleanup profile — see logs.")
        if not ops:
            # shipped copy, verbatim.
            return Reply(BLOCKED, f"Profile `{slug}` produced no "
                                  "operations.")
        staged = 0
        for op in ops:
            try:
                await section_card.stage_custom(guild_id, SLUG, op)
                staged += 1
            except Exception:  # noqa: BLE001 — per-op isolation (shipped)
                logger.exception(
                    "cleanup: profile append failed (slug=%s, target=%s)",
                    slug, op.payload.get("scope_id"))
        await section_card.mark_step_in_progress(req, SLUG)
        try:
            pending = await wizard.staged_ops_count(guild_id)
        except Exception:  # noqa: BLE001 — the shipped count soft-fail
            logger.exception("cleanup: setup_draft.count failed (profile)")
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

    if not is_registered(HandlerRef("setup.cleanup_detail_render")):
        handler("setup.cleanup_detail_render")(_render_cleanup_detail)
    if not is_registered(PanelRef(CLEANUP_DETAIL_PANEL_ID)):
        panel(CLEANUP_DETAIL_PANEL_ID)(cleanup_detail_spec)


def _register_section() -> None:
    from sb.domain.setup import section_card

    section_card.register_recommended_builder(SLUG, recommended_cleanup_ops)
    section_card.register_customize_panel(SLUG, CLEANUP_DETAIL_PANEL_ID)
    section_card.register_section_card(SLUG, detected_state=_DETECTED_STATE)


_ensure_providers()
_register()
_register_panels()
_register_section()
_register_set_cleanup_op_kind()


def ensure_setup_cleanup_refs() -> None:
    _ensure_providers()
    _register()
    _register_panels()
    _register_section()
    _register_set_cleanup_op_kind()

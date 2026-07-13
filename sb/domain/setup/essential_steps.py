"""ESSENTIAL SETUP steps 2–8 (the essential-steps slice), ported from
the oracle (menno420/superbot, disbot/views/setup/essential_setup.py,
read from the LOCAL oracle clone):

* the FLOW SPINE (``EssentialFlow``): the ordered 8-step list, the
  ``Step X of N`` counter, applied/skipped recording, and the
  best-effort ``persist_progress`` position write (the oracle's
  migration-099 ``set_essential_step`` — here the K7
  ``setup.set_essential_step`` op over the same ``essential_step``
  column; reaching the summary clears the anchor and marks the session
  complete, the oracle order);
* the SEVEN step cards after Step-1's server-type starter set — copy,
  labels, guards and applied-summary lines verbatim; every Save applies
  IMMEDIATELY through the audited kernel seams (the oracle's
  direct-apply doctrine, "save each step instantly"):
  - 👋 **Greet new members**: ``welcome.enabled``/``join_enabled``
    scalars + the ``welcome.channel``/``welcome.entry_role`` BINDINGS
    (the oracle wrote them as settings-table strings; this
    architecture declares them BindingSpec rows, so the audited
    ``settings.bind`` lane carries them — ledgered adaptation);
  - 🛡️ **Set your moderators**: the moderator role lands in
    ``governance.moderator_tier_role_id`` (the ADR-008 tier grant —
    the oracle's ``moderation.moderator_role`` key does not exist in
    this architecture's vocabulary; the tier setting is what actually
    lets the role warn/remove, ledgered adaptation) +
    ``moderation.dm_on_action``;
  - 🧹 **Block spam and bad links**: ``automod.enabled`` + the four
    filter toggles;
  - 📋 **Choose a log channel**: auto-create #mod-log / #server-log
    through the armed channel-state port (create + the shipped
    audit/lifecycle companion pair — the channel domain's create
    posture), then ``logging.enabled`` + the three activity flags +
    the ``logging.mod_channel``/``events_channel`` binds;
  - 🏅 **Reward active members** (two screens): XP-rate scalars, the
    reward role (auto-create @Regular through the role-provisioning
    port + companions / create-named / reuse-existing), then ONE
    ``role.set_threshold`` run carrying the level and/or time
    thresholds (the oracle's set_xp_threshold + set_time_threshold
    wrote different columns of the same row; the K7 leg is a full-row
    upsert, so the two writes fold into one op run — ledgered);
  - 🎫 **Set up a help desk**: the audited ``ticket.update_config`` op
    (enabled + staff_role_id + log_channel_id — the ticket setup
    panel's exact seam);
  - 🚪 **Where can people use commands?**: the K7
    ``platform.set_access_mode`` (+ ``set_access_channels`` for the
    allow-list mode) ops — the same policy the runtime command gate
    reads;
* the closing **EssentialSummaryView** (All done · ✨ More to set up ·
  🔎 Check my setup), the **ExtrasMenuView** (copy verbatim), and the
  **Check-my-setup** health read (the oracle ``setup_readiness.collect``
  fold — configured = any explicit setting row or binding row for the
  subsystem — over the declared-settings + bindings reads);
* the RESTART-RESUME lane: the persistent one-button
  **EssentialSetupResumeView** (static custom_id
  ``essential_setup:resume``, compat-pinned) rebuilds the flow at the
  saved ``essential_step`` and lands on the right card.

Kernel-idiom divergences, ledgered (the wizard.py adaptation doctrine —
same copy, same labels, same flow; only the seams differ):

* the oracle swapped views in place (``safe_edit``); navigation here
  opens the destination panel through ``open_panel`` (the #295
  precedent) and per-pick re-renders ride ``refresh_session_view``;
* flow state is held per ``guild:user`` in memory exactly like the
  oracle's author-bound view attributes — a restart forgets the picks
  (the oracle's views died too); only the POSITION survives, through
  the persisted ``essential_step`` (a bare keyed UPDATE — no session
  row means a silent no-op, the set_depth semantics; the ``!setup``
  entry mints no session row, the golden-pinned empty delta, so
  cross-restart resume arms once a session row exists);
* ephemeral sends (step guards, the health check, the extras terminal
  acks) answer as text replies carrying the embed copy verbatim;
* the summary's **All done** disabled-buttons terminal answers as a
  text reply carrying the summary headline (the component model keeps
  no per-message disable lane on refresh);
* the resume gate rides the ported ``can_apply_setup`` ladder (the
  oracle's ``is_setup_admin`` also admitted bare administrators;
  administrators-without-delegation stay read-only in this
  architecture — the wizard.py gate doctrine) with the shipped
  refusal copy;
* the oracle's on-ready revive sweep (``revive_essential_flows`` — the
  bot-lifecycle edit of interrupted flow messages) is PORTED: the
  app-boot seam is the kernel boot-hook registry
  (sb/kernel/lifecycle/boot_hooks.py) and the sweep lives in
  sb/domain/setup/resume.py (ORDER 019 item 5a).

NO GOLDEN drives any of these components (the panels.py module pin);
the oracle SOURCES pin the copy, and every golden-pinned OPEN render
stays byte-identical.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = [
    "COMMANDS_PANEL_ID",
    "EXTRAS_PANEL_ID",
    "GREET_PANEL_ID",
    "HELPDESK_PANEL_ID",
    "LOG_PANEL_ID",
    "MODS_PANEL_ID",
    "REWARD_PANEL_ID",
    "REWARD_ROLE_PANEL_ID",
    "RESUME_PANEL_ID",
    "SPAM_PANEL_ID",
    "SUMMARY_PANEL_ID",
    "EssentialFlow",
    "ensure_essential_steps_refs",
    "flow_state",
    "reset_essential_state_for_tests",
]

logger = logging.getLogger("sb.domain.setup")

GREET_PANEL_ID = "setup.essential_greet"
MODS_PANEL_ID = "setup.essential_mods"
SPAM_PANEL_ID = "setup.essential_spam"
LOG_PANEL_ID = "setup.essential_log"
REWARD_PANEL_ID = "setup.essential_reward"
REWARD_ROLE_PANEL_ID = "setup.essential_reward_role"
HELPDESK_PANEL_ID = "setup.essential_helpdesk"
COMMANDS_PANEL_ID = "setup.essential_commands"
SUMMARY_PANEL_ID = "setup.essential_summary"
EXTRAS_PANEL_ID = "setup.essential_extras"
RESUME_PANEL_ID = "setup.essential_resume"

#: the 8-step spine, in flow order (essential_setup.EssentialFlow._steps
#: — index 0 is the wizard-lifecycle slice's Step-1 card).
STEP_TITLES: tuple[str, ...] = (
    "What kind of server is this?",
    "Greet new members",
    "Set your moderators",
    "Block spam and bad links",
    "Choose a log channel",
    "Reward active members",
    "Set up a help desk",
    "Where can people use commands?",
)

_TOTAL = len(STEP_TITLES)


# --- shipped data, verbatim -------------------------------------------------------

#: plain-language default names for the channels we offer to create.
_NEW_MOD_CHANNEL_NAME = "mod-log"
_NEW_ACTIVITY_CHANNEL_NAME = "server-log"

#: (setting name, operator-facing label) — essential_setup._SPAM_FILTERS.
_SPAM_FILTERS: tuple[tuple[str, str], ...] = (
    ("spam_enabled", "Repeated spam"),
    ("invites_enabled", "Invite links"),
    ("caps_enabled", "ALL-CAPS shouting"),
    ("mentions_enabled", "Mass pings"),
)

#: (logging flag, operator label, default-on) — essential_setup.
#: _ACTIVITY_TYPES (message logging defaults OFF, the privacy trade-off).
_ACTIVITY_TYPES: tuple[tuple[str, str, bool], ...] = (
    ("members_enabled", "Members joining & leaving", True),
    ("roles_enabled", "Role changes", True),
    ("messages_enabled", "Message edits & deletions", False),
)
_DEFAULT_ACTIVITY: frozenset[str] = frozenset(
    flag for flag, _, on in _ACTIVITY_TYPES if on)

#: reward triggers / role sources / suggested names, verbatim.
_REWARD_TYPES: tuple[tuple[str, str], ...] = (
    ("level", "When members reach a level"),
    ("time", "When members stay a while"),
)
_ROLE_SOURCES: tuple[tuple[str, str], ...] = (
    ("recommended", "Recommended — make a @Regular role"),
    ("create", "Create a role I name"),
    ("existing", "Use a role I already have"),
)
_SUGGESTED_ROLE_NAMES: tuple[str, ...] = (
    "Regular", "Member", "Trusted", "Veteran", "Active", "VIP")
_DEFAULT_ROLE_NAME = "Regular"
_DEFAULT_LEVEL = 10
_DEFAULT_DAYS = 30

#: (stored mode, operator label, plain description) — essential_setup.
#: _CMD_ACCESS_CHOICES (the three modes mirror sb/kernel/authority/
#: channel_access.AccessMode verbatim).
_CMD_ACCESS_CHOICES: tuple[tuple[str, str, str], ...] = (
    ("all_channels", "Anywhere on the server",
     "Members can use commands in every channel."),
    ("selected_channels", "Only in channels I choose",
     "Commands work only in the channels you pick below."),
    ("disabled_except_bootstrap", "Off for members — admins only",
     "Members can't use commands; you keep admin access for setup."),
)
_CMD_ACCESS_LABELS: dict[str, str] = {
    mode: label for mode, label, _ in _CMD_ACCESS_CHOICES}

#: the extras menu (essential_setup._EXTRAS, verbatim — native giveaways
#: intentionally absent, the oracle's own note).
_EXTRAS: tuple[tuple[str, str, str, str], ...] = (
    ("🏆", "Hall of Fame",
     "pin the messages your members love the most", "!starboard"),
    ("🔢", "Live member counts",
     "show member and online counts right in your channel list",
     "!counters"),
    ("🛡️", "Raid & new-account protection",
     "slow down raids and hold brand-new accounts for a look",
     "!security"),
    ("🖼️", "Image filtering",
     "catch unwanted images automatically", "!imagemod"),
    ("🙏", "Thanks & Karma",
     "let members thank each other and build up reputation", "!karma"),
    ("🤖", "AI helper",
     "let members ask the bot questions in plain language", "!aimenu"),
    ("🎭", "Reaction roles",
     "let members pick their own roles by reacting", "!reactroles"),
)

#: essentials shown in the health check (essential_setup.
#: _CHECK_ESSENTIALS, verbatim).
_CHECK_ESSENTIALS: tuple[tuple[str, str], ...] = (
    ("welcome", "Greeting new members"),
    ("moderation", "Moderator tools"),
    ("automod", "Spam & bad-link protection"),
    ("logging", "Activity logging"),
    ("xp", "Member rewards"),
    ("ticket", "Help desk"),
)

#: shipped resume refusal, verbatim (EssentialSetupResumeView.resume).
_RESUME_GATE_MSG = ("Only the server owner, an administrator, or a delegated "
                    "setup admin can resume setup.")


# --- flow state (the oracle EssentialFlow + per-step view attributes) --------------

@dataclass
class EssentialFlow:
    """The oracle ``EssentialFlow`` + the step views' pick attributes,
    held per ``guild:user`` in memory (the wizard.py _ESSENTIAL_PICKS
    precedent — restart forgets it exactly like the oracle's views)."""

    index: int = 0
    applied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    # step 2 — greet
    greet_channel_id: int | None = None
    greet_role_id: int | None = None
    # step 3 — moderators
    mod_role_id: int | None = None
    mod_dm_on: bool = True
    # step 4 — spam
    spam_filters: set[str] = field(
        default_factory=lambda: {key for key, _ in _SPAM_FILTERS})
    # step 5 — log channels
    log_activity: set[str] = field(
        default_factory=lambda: set(_DEFAULT_ACTIVITY))
    log_mod_channel_id: int | None = None
    log_activity_channel_id: int | None = None
    log_mod_name: str | None = None
    log_activity_name: str | None = None
    # step 6 — rewards
    reward_phase: str = "config"          # "config" | "roles"
    reward_xp_rate: str = "keep"
    reward_types: set[str] = field(default_factory=set)
    reward_role_source: str = "recommended"
    reward_new_role_name: str | None = None
    reward_existing_role_id: int | None = None
    reward_existing_role_name: str | None = None
    # step 7 — help desk
    helpdesk_staff_role_id: int | None = None
    helpdesk_log_channel_id: int | None = None
    # step 8 — command access
    cmd_mode: str = "all_channels"
    cmd_channel_ids: list[int] = field(default_factory=list)

    @property
    def total(self) -> int:
        return _TOTAL

    @property
    def done(self) -> bool:
        return self.index >= self.total

    def step_counter(self) -> str:
        return f"Step {self.index + 1} of {self.total}"

    def record_applied(self, line: str) -> None:
        self.applied.append(line)

    def record_skipped(self, line: str) -> None:
        self.skipped.append(line)


_FLOWS: dict[str, EssentialFlow] = {}


def _flow_key(guild_id: int, user_id: int) -> str:
    return f"{int(guild_id)}:{int(user_id)}"


def flow_state(guild_id: int, user_id: int) -> EssentialFlow:
    key = _flow_key(guild_id, user_id)
    state = _FLOWS.get(key)
    if state is None:
        state = EssentialFlow()
        _FLOWS[key] = state
    return state


def reset_essential_state_for_tests() -> None:
    _FLOWS.clear()


def _req_flow(req) -> EssentialFlow:
    return flow_state(int(req.guild_id or 0),
                      int(getattr(req.actor, "user_id", 0) or 0))


def _ctx_flow(ctx) -> EssentialFlow:
    return flow_state(int(ctx.guild_id or 0),
                      int(getattr(ctx.actor, "user_id", 0) or 0))


# --- navigation (EssentialFlow.persist_progress + _StepView._show_current) --------

#: flow index → the step's panel (index 0 = the Step-1 card the
#: wizard-lifecycle slice armed; the reward step's "roles" screen is the
#: same index, phase-routed).
def _panel_for_index(state: EssentialFlow) -> str:
    from sb.domain.setup.panels import ESSENTIAL_PANEL_ID

    if state.done:
        return SUMMARY_PANEL_ID
    if state.index == 5 and state.reward_phase == "roles":
        return REWARD_ROLE_PANEL_ID
    return (ESSENTIAL_PANEL_ID, GREET_PANEL_ID, MODS_PANEL_ID,
            SPAM_PANEL_ID, LOG_PANEL_ID, REWARD_PANEL_ID,
            HELPDESK_PANEL_ID, COMMANDS_PANEL_ID)[state.index]


async def persist_progress(req, state: EssentialFlow) -> None:
    """The oracle ``persist_progress`` verbatim semantics: best-effort —
    a DB hiccup must never break the wizard; reaching the summary clears
    the anchor and marks the session complete (the oracle order), else
    the position lands in ``essential_step`` (K7 ops over the same
    columns; no session row = the silent-no-op UPDATE semantics)."""
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    try:
        if state.done:
            await engine.run(WorkflowRef("setup.clear_essential_anchor"),
                             ctx_from_request(req, {}))
            await engine.run(WorkflowRef("setup.mark_complete"),
                             ctx_from_request(req, {}))
        else:
            await engine.run(WorkflowRef("setup.set_essential_step"),
                             ctx_from_request(req, {"step": state.index}))
    except Exception:  # noqa: BLE001 — the oracle's own posture
        logger.exception(
            "essential setup: persist_progress failed (guild=%s)",
            req.guild_id)


async def _show_current(req, state: EssentialFlow) -> None:
    """The ``_StepView._show_current`` twin: land on the flow's current
    card (open_panel — the ledgered navigation lane), then persist the
    new position."""
    from sb.domain.setup.wizard import _open

    await _open(req, _panel_for_index(state))
    await persist_progress(req, state)


async def _advance(req, state: EssentialFlow) -> None:
    state.index += 1
    await _show_current(req, state)


async def _complete_step(req, state: EssentialFlow, line: str) -> None:
    """``_StepView.complete``: record the applied change and advance."""
    state.record_applied(line)
    await _advance(req, state)


async def _skip_step(req, state: EssentialFlow, title: str) -> None:
    state.record_skipped(title)
    await _advance(req, state)


# --- the audited write seams --------------------------------------------------------

async def _set(req, subsystem: str, name: str, value: object) -> None:
    """One audited scalar write (``_StepView._set`` → the wizard.py K7
    ``settings.set_scalar`` helper); non-SUCCESS raises so each step's
    shipped error copy answers."""
    from sb.domain.setup import wizard

    result = await wizard._write_setting(req, subsystem, name, value)
    if result.outcome != SUCCESS:
        raise RuntimeError(
            f"settings.set_scalar {subsystem}.{name} → {result.outcome}")


async def _bind(req, subsystem: str, name: str, kind: str,
                resource_id: int) -> None:
    """One audited binding write (the oracle ``LogChannelStep._bind`` /
    BindingMutationPipeline twin — the K7 ``settings.bind`` op)."""
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    result = await engine.run(
        WorkflowRef("settings.bind"),
        ctx_from_request(req, {"subsystem": subsystem, "name": name,
                               "kind": kind,
                               "resource_id": int(resource_id)}))
    if result.outcome != SUCCESS:
        raise RuntimeError(
            f"settings.bind {subsystem}.{name} → {result.outcome}")


async def _create_channel(req, name: str) -> int | None:
    """Create *name* through the armed channel-state port + the shipped
    audit/lifecycle companion pair (the channel domain's create posture
    — a created channel never goes unaudited). Returns the new id, or
    ``None`` after the failure was logged (the caller surfaces the
    shipped copy and stops without writing anything)."""
    import uuid

    from sb.domain.channel import service as channel_service

    gid = int(req.guild_id or 0)
    actions = channel_service.active_actions()  # the D-0077 port binding
    try:
        cid = await actions.create_text_channel(
            gid, name=name, overwrites=(), parent_id=None, reason=None)
    except Exception as exc:  # noqa: BLE001 — port refusal / live Forbidden
        logger.warning(
            "essential setup: log channel %r create failed (guild=%s): %s",
            name, gid, exc)
        return None
    mutation_id = str(uuid.uuid4())
    actor_id = int(getattr(req.actor, "user_id", 0) or 0)
    await channel_service.emit_channel_audit(
        gid, mutation_id=mutation_id, operation="create",
        target=f"channel:{cid}", new_value=f"create channel '{name}'",
        actor_id=actor_id, actor_type="admin")
    await channel_service.emit_channel_lifecycle(
        gid, mutation_id=mutation_id, operation="create",
        outcome="success", applied=[int(cid)], failed=[])
    return int(cid)


async def _create_role(req, name: str) -> int | None:
    """Create the reward role through the role-provisioning port + the
    shipped companion pair (the `!createrole` lane's shape — ONE
    mutation_id shared by audit fact and lifecycle advisory)."""
    import uuid

    from sb.domain.role import service as role_service

    gid = int(req.guild_id or 0)
    try:
        rid = await role_service.active_provisioning().create_guild_role(
            gid, name=name, color=0, reason=None)
    except Exception as exc:  # noqa: BLE001 — port refusal / live Forbidden
        logger.warning(
            "essential setup: reward role create failed (guild=%s): %s",
            gid, exc)
        return None
    mutation_id = str(uuid.uuid4())
    actor_id = int(getattr(req.actor, "user_id", 0) or 0)
    await role_service.emit_role_audit(
        gid, mutation_id=mutation_id, mutation_type="role_create",
        target=f"role:{rid}", new_value=f"create role '{name}'",
        actor_id=actor_id, actor_type="admin")
    await role_service.emit_role_lifecycle(
        gid, mutation_id=mutation_id, operation="create",
        outcome="success", applied=[int(rid)], failed=[])
    return int(rid)


def _picked_int(req) -> int | None:
    values = tuple(req.args.get("values", ()) or ())
    if not values:
        return None
    raw = str(values[0])
    return int(raw) if raw.lstrip("-").isdigit() else None


async def _refresh(req, params: dict | None = None) -> bool:
    from sb.domain.setup.wizard import _refresh_own_panel

    return await _refresh_own_panel(req, dict(params or {}))


# --- the check-my-setup health read (setup_readiness.collect, folded) ---------------

async def _configured_subsystems(guild_id: int) -> set[str]:
    """Subsystems with ANY explicit configuration: an explicit settings
    row (mapped back through the declared persisted keys) or a binding
    row — the oracle's ``(sr.bindings_bound + sr.settings_configured)
    > 0`` fold."""
    from sb.kernel import settings as ksettings
    from sb.kernel.db.settings import fetchall_bindings, get_setting_rows

    key_to_subsystem = {
        ksettings.persisted_key(decl.subsystem, decl.name): decl.subsystem
        for decl in ksettings.iter_declarations()}
    configured: set[str] = set()
    rows = await get_setting_rows(int(guild_id))
    for key in rows:
        subsystem = key_to_subsystem.get(key)
        if subsystem:
            configured.add(subsystem)
    for row in await fetchall_bindings(int(guild_id)):
        configured.add(str(row["subsystem"]))
    return configured


async def build_check_setup_text(guild_id: int) -> str:
    """The "Check my setup" health check (build_check_setup_embed's copy
    verbatim, carried as the ledgered text-reply seam)."""
    try:
        configured = await _configured_subsystems(guild_id)
    except Exception:  # noqa: BLE001 — headless / no DB ⇒ nothing configured
        logger.debug("essential setup: health read failed", exc_info=True)
        configured = set()
    lines: list[str] = []
    done = 0
    for key, label in _CHECK_ESSENTIALS:
        ok = key in configured
        if ok:
            done += 1
        lines.append(f"{'✅' if ok else '➖'} {label}")
    total = len(_CHECK_ESSENTIALS)
    if done == total:
        headline = "🎉 Everything essential is set up — nice work!"
    elif done == 0:
        headline = ("Nothing essential is set up yet — run setup to get "
                    "started.")
    else:
        headline = f"You've set up **{done} of {total}** essentials so far."
    text = ("🔎 **How set up are you?**\n" + headline + "\n\n**Essentials**\n"
            + "\n".join(lines))
    if done < total:
        text += ("\n\n**Want to finish the rest?**\n"
                 "Run setup again any time — each step saves the moment you "
                 "press its button, so you only do what's left.")
    return text


# --- panel specs ---------------------------------------------------------------------

def _nav_actions(prefix: str, skip_label: str, skip_handler: str,
                 back_handler: str = "setup.essential_back"):
    """The shared bottom-row nav pair (``_BackButton`` + ``_SkipButton``
    — every step past index 0 carries Back; labels verbatim). Action ids
    carry the panel prefix — custom_id leaves are namespace-claimed per
    subsystem, so a bare shared ``nav_back`` collides."""
    from sb.spec.panels import ActionStyle, PanelActionSpec
    from sb.spec.refs import HandlerRef

    return (
        PanelActionSpec(action_id=f"{prefix}_back", label="Back",
                        style=ActionStyle.SECONDARY,
                        handler=HandlerRef(back_handler)),
        PanelActionSpec(action_id=f"{prefix}_skip", label=skip_label,
                        style=ActionStyle.SECONDARY,
                        handler=HandlerRef(skip_handler)),
    )


def _panel(panel_id: str, title: str, *, actions, selectors=(), rows,
           renderer: str, justification: str):
    from sb.spec.panels import (
        Audience, EmbedFrameSpec, FooterMode, LayoutSpec, NavigationSpec,
        PageSpec, PanelSpec,
    )
    from sb.spec.refs import HandlerRef

    return PanelSpec(
        panel_id=panel_id, subsystem="setup", title=title,
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        actions=tuple(actions), selectors=tuple(selectors),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=tuple(rows)),)),
        renderer_override=HandlerRef(renderer),
        justification=justification,
        session_lifecycle=True,
    )


_STEP_JUSTIFICATION = (
    "the shipped step card is flow-state-parameterized end to end (the "
    "picked-value fields, the 'Step X of N' footer literal — "
    "essential_setup.py render()) — outside the static grammar "
    "vocabulary; the override renders through the grammar and composes "
    "the embed (no golden pins this panel — the oracle source does).")


def greet_spec():
    """Step 2 — 👋 Greet new members (GreetMembersStep, verbatim)."""
    from sb.spec.panels import (
        ActionStyle, PanelActionSpec, SelectorKind, SelectorSpec,
    )
    from sb.spec.refs import HandlerRef

    return _panel(
        GREET_PANEL_ID, "👋 Greet new members",
        selectors=(
            SelectorSpec(
                selector_id="greet_channel", kind=SelectorKind.CHANNEL,
                on_select=HandlerRef("setup.essential_greet_channel"),
                placeholder="Where should the welcome message appear?"),
            SelectorSpec(
                selector_id="greet_role", kind=SelectorKind.ROLE,
                on_select=HandlerRef("setup.essential_greet_role"),
                min_values=0, max_values=1,
                placeholder="Give newcomers a role (optional)…"),
        ),
        actions=(
            PanelActionSpec(
                action_id="greet_save", label="Save & continue", emoji="👋",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.essential_greet_save")),
        ) + _nav_actions("greet", "Skip greetings",
                         "setup.essential_greet_skip"),
        rows=(("greet_channel",), ("greet_role",), ("greet_save",),
              ("greet_back", "greet_skip")),
        renderer="setup.essential_greet_render",
        justification=_STEP_JUSTIFICATION)


def mods_spec():
    """Step 3 — 🛡️ Set your moderators (ModeratorsStep, verbatim)."""
    from sb.spec.panels import (
        ActionStyle, PanelActionSpec, SelectorKind, SelectorSpec,
    )
    from sb.spec.refs import HandlerRef

    return _panel(
        MODS_PANEL_ID, "🛡️ Set your moderators",
        selectors=(
            SelectorSpec(
                selector_id="mods_role", kind=SelectorKind.ROLE,
                on_select=HandlerRef("setup.essential_mods_role"),
                placeholder="Which role can warn and remove people?"),
        ),
        actions=(
            PanelActionSpec(
                action_id="mods_dm_toggle", label="Tell members why: ON",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.essential_mods_dm_toggle")),
            PanelActionSpec(
                action_id="mods_save", label="Save & continue", emoji="🛡️",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.essential_mods_save")),
        ) + _nav_actions("mods", "Skip moderators",
                         "setup.essential_mods_skip"),
        rows=(("mods_role",), ("mods_dm_toggle",), ("mods_save",),
              ("mods_back", "mods_skip")),
        renderer="setup.essential_mods_render",
        justification=_STEP_JUSTIFICATION)


_SPAM_OPTIONS_PROVIDER = "setup.essential_spam_options"
_ACTIVITY_OPTIONS_PROVIDER = "setup.essential_activity_options"
_XP_RATE_OPTIONS_PROVIDER = "setup.essential_xp_rate_options"
_REWARD_TYPE_OPTIONS_PROVIDER = "setup.essential_reward_type_options"
_ROLE_SOURCE_OPTIONS_PROVIDER = "setup.essential_role_source_options"
_ROLE_NAME_OPTIONS_PROVIDER = "setup.essential_role_name_options"
_CMD_MODE_OPTIONS_PROVIDER = "setup.essential_cmd_mode_options"


def spam_spec():
    """Step 4 — 🧹 Block spam and bad links (BlockSpamStep, verbatim)."""
    from sb.spec.panels import (
        ActionStyle, PanelActionSpec, SelectorKind, SelectorSpec,
    )
    from sb.spec.refs import HandlerRef, ProviderRef

    return _panel(
        SPAM_PANEL_ID, "🧹 Block spam and bad links",
        selectors=(
            SelectorSpec(
                selector_id="spam_filters", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.essential_spam_pick"),
                options_source=ProviderRef(_SPAM_OPTIONS_PROVIDER),
                min_values=0, max_values=len(_SPAM_FILTERS),
                placeholder="What should I clean up? (all on by default)"),
        ),
        actions=(
            PanelActionSpec(
                action_id="spam_save", label="Save & continue", emoji="🧹",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.essential_spam_save")),
        ) + _nav_actions("spam", "Skip spam protection",
                         "setup.essential_spam_skip"),
        rows=(("spam_filters",), ("spam_save",), ("spam_back", "spam_skip")),
        renderer="setup.essential_spam_render",
        justification=_STEP_JUSTIFICATION)


def log_spec():
    """Step 5 — 📋 Choose a log channel (LogChannelStep, verbatim; the
    ✏️ names button carries the G-10 modal form twin of
    _ChannelNamesModal)."""
    from sb.spec.outcomes import DeferMode
    from sb.spec.panels import (
        ActionStyle, ModalFieldSpec, ModalSpec, PanelActionSpec,
        SelectorKind, SelectorSpec,
    )
    from sb.spec.refs import HandlerRef, ProviderRef

    names_modal = ModalSpec(
        modal_id="setup.essential_log_names_form",
        title="Name the new channels",
        fields=(
            ModalFieldSpec(field_id="mod_name",
                           label="Moderation log channel name",
                           required=False, max_length=90),
            ModalFieldSpec(field_id="activity_name",
                           label="Activity log channel name",
                           required=False, max_length=90),
        ),
        on_submit=HandlerRef("setup.essential_log_names"))
    return _panel(
        LOG_PANEL_ID, "📋 Choose a log channel",
        selectors=(
            SelectorSpec(
                selector_id="log_activity", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.essential_log_activity"),
                options_source=ProviderRef(_ACTIVITY_OPTIONS_PROVIDER),
                min_values=0, max_values=len(_ACTIVITY_TYPES),
                placeholder="What should the activity channel log?"),
            SelectorSpec(
                selector_id="log_mod_channel", kind=SelectorKind.CHANNEL,
                on_select=HandlerRef("setup.essential_log_mod_pick"),
                min_values=0, max_values=1,
                placeholder="Moderation log channel (or leave empty)…"),
            SelectorSpec(
                selector_id="log_activity_channel",
                kind=SelectorKind.CHANNEL,
                on_select=HandlerRef("setup.essential_log_activity_pick"),
                min_values=0, max_values=1,
                placeholder="Activity log channel (or leave empty)…"),
        ),
        actions=(
            PanelActionSpec(
                action_id="log_names", label="✏️ Name the new channel(s)",
                style=ActionStyle.SECONDARY,
                defer_mode=DeferMode.MODAL, modal=names_modal,
                handler=HandlerRef("setup.essential_log_names")),
            PanelActionSpec(
                action_id="log_save", label="Save & continue", emoji="📋",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.essential_log_save")),
        ) + _nav_actions("log", "Skip logging", "setup.essential_log_skip"),
        rows=(("log_activity",), ("log_mod_channel",),
              ("log_activity_channel",), ("log_names", "log_save"),
              ("log_back", "log_skip")),
        renderer="setup.essential_log_render",
        justification=_STEP_JUSTIFICATION)


def reward_spec():
    """Step 6 screen 1 — 🏅 Reward active members (RewardActivityStep's
    config phase, verbatim)."""
    from sb.spec.panels import (
        ActionStyle, PanelActionSpec, SelectorKind, SelectorSpec,
    )
    from sb.spec.refs import HandlerRef, ProviderRef

    return _panel(
        REWARD_PANEL_ID, "🏅 Reward active members",
        selectors=(
            SelectorSpec(
                selector_id="reward_rate", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.essential_reward_rate"),
                options_source=ProviderRef(_XP_RATE_OPTIONS_PROVIDER),
                placeholder="How fast should members earn XP?"),
            SelectorSpec(
                selector_id="reward_types", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.essential_reward_types"),
                options_source=ProviderRef(_REWARD_TYPE_OPTIONS_PROVIDER),
                min_values=0, max_values=len(_REWARD_TYPES),
                placeholder="Give a role as a reward for… (optional)"),
        ),
        actions=(
            PanelActionSpec(
                action_id="reward_next", label="Save & continue", emoji="🏅",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.essential_reward_next")),
        ) + _nav_actions("reward", "Skip rewards",
                         "setup.essential_reward_skip"),
        rows=(("reward_rate",), ("reward_types",), ("reward_next",),
              ("reward_back", "reward_skip")),
        renderer="setup.essential_reward_render",
        justification=_STEP_JUSTIFICATION)


def reward_role_spec():
    """Step 6 screen 2 — 🏅 Choose the reward role (RewardActivityStep's
    roles phase, verbatim; ✏️ Type a name is the G-10 form twin of
    _RoleNameModal; Back returns to screen 1)."""
    from sb.spec.outcomes import DeferMode
    from sb.spec.panels import (
        ActionStyle, ModalFieldSpec, ModalSpec, PanelActionSpec,
        SelectorKind, SelectorSpec,
    )
    from sb.spec.refs import HandlerRef, ProviderRef

    name_modal = ModalSpec(
        modal_id="setup.essential_reward_name_form",
        title="Name the reward role",
        fields=(
            ModalFieldSpec(field_id="role_name", label="Role name",
                           required=False, max_length=90),
        ),
        on_submit=HandlerRef("setup.essential_reward_typed_name"))
    return _panel(
        REWARD_ROLE_PANEL_ID, "🏅 Choose the reward role",
        selectors=(
            SelectorSpec(
                selector_id="reward_source", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.essential_reward_source"),
                options_source=ProviderRef(_ROLE_SOURCE_OPTIONS_PROVIDER),
                placeholder="Where should the reward role come from?"),
            SelectorSpec(
                selector_id="reward_name", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.essential_reward_name"),
                options_source=ProviderRef(_ROLE_NAME_OPTIONS_PROVIDER),
                placeholder="Name for the new role…"),
            SelectorSpec(
                selector_id="reward_existing", kind=SelectorKind.ROLE,
                on_select=HandlerRef("setup.essential_reward_existing"),
                min_values=0, max_values=1,
                placeholder="Pick the role to grant…"),
        ),
        actions=(
            PanelActionSpec(
                action_id="reward_type_name", label="✏️ Type a name",
                style=ActionStyle.SECONDARY,
                defer_mode=DeferMode.MODAL, modal=name_modal,
                handler=HandlerRef("setup.essential_reward_typed_name")),
            PanelActionSpec(
                action_id="reward_save", label="Save & continue", emoji="🏅",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.essential_reward_save")),
        ) + _nav_actions("reward_role", "Skip rewards",
                         "setup.essential_reward_skip",
                         back_handler="setup.essential_reward_back"),
        rows=(("reward_source",), ("reward_name",), ("reward_existing",),
              ("reward_type_name", "reward_save"),
              ("reward_role_back", "reward_role_skip")),
        renderer="setup.essential_reward_role_render",
        justification=_STEP_JUSTIFICATION)


def helpdesk_spec():
    """Step 7 — 🎫 Set up a help desk (HelpDeskStep, verbatim)."""
    from sb.spec.panels import (
        ActionStyle, PanelActionSpec, SelectorKind, SelectorSpec,
    )
    from sb.spec.refs import HandlerRef

    return _panel(
        HELPDESK_PANEL_ID, "🎫 Set up a help desk",
        selectors=(
            SelectorSpec(
                selector_id="helpdesk_staff", kind=SelectorKind.ROLE,
                on_select=HandlerRef("setup.essential_helpdesk_staff"),
                placeholder="Who answers support requests? (staff role)"),
            SelectorSpec(
                selector_id="helpdesk_log", kind=SelectorKind.CHANNEL,
                on_select=HandlerRef("setup.essential_helpdesk_log"),
                placeholder="Where to save closed-request logs? (optional)"),
        ),
        actions=(
            PanelActionSpec(
                action_id="helpdesk_save", label="Save & continue",
                emoji="🎫", style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.essential_helpdesk_save")),
        ) + _nav_actions("helpdesk", "Skip help desk",
                         "setup.essential_helpdesk_skip"),
        rows=(("helpdesk_staff",), ("helpdesk_log",), ("helpdesk_save",),
              ("helpdesk_back", "helpdesk_skip")),
        renderer="setup.essential_helpdesk_render",
        justification=_STEP_JUSTIFICATION)


def commands_spec():
    """Step 8 — 🚪 Where can people use commands? (CommandChannelsStep,
    verbatim; the allow-list picker shows only in the
    selected-channels mode — the renderer filter)."""
    from sb.spec.panels import (
        ActionStyle, PanelActionSpec, SelectorKind, SelectorSpec,
    )
    from sb.spec.refs import HandlerRef, ProviderRef

    return _panel(
        COMMANDS_PANEL_ID, "🚪 Where can people use commands?",
        selectors=(
            SelectorSpec(
                selector_id="cmd_mode", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.essential_commands_mode"),
                options_source=ProviderRef(_CMD_MODE_OPTIONS_PROVIDER),
                placeholder="Where can people use commands?"),
            SelectorSpec(
                selector_id="cmd_channels", kind=SelectorKind.CHANNEL,
                on_select=HandlerRef("setup.essential_commands_channels"),
                min_values=0, max_values=25,
                placeholder="Pick the channels where commands should "
                            "work…"),
        ),
        actions=(
            PanelActionSpec(
                action_id="cmd_save", label="Save & continue", emoji="🚪",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.essential_commands_save")),
        ) + _nav_actions("cmd", "Skip — leave as is",
                         "setup.essential_commands_skip"),
        rows=(("cmd_mode",), ("cmd_channels",), ("cmd_save",),
              ("cmd_back", "cmd_skip")),
        renderer="setup.essential_commands_render",
        justification=_STEP_JUSTIFICATION)


def summary_spec():
    """The closing summary (EssentialSummaryView: ✅ All done ·
    ✨ More to set up · 🔎 Check my setup — labels/styles verbatim)."""
    from sb.spec.panels import ActionStyle, PanelActionSpec
    from sb.spec.refs import HandlerRef

    return _panel(
        SUMMARY_PANEL_ID, "✅ Setup complete",
        actions=(
            PanelActionSpec(
                action_id="summary_done", label="All done", emoji="✅",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.essential_summary_done")),
            PanelActionSpec(
                action_id="summary_extras", label="More to set up",
                emoji="✨", style=ActionStyle.PRIMARY,
                handler=HandlerRef("setup.essential_summary_extras")),
            PanelActionSpec(
                action_id="summary_check", label="Check my setup",
                emoji="🔎", style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.essential_summary_check")),
        ),
        rows=(("summary_done",), ("summary_extras", "summary_check")),
        renderer="setup.essential_summary_render",
        justification=(
            "the shipped summary card is flow-state-parameterized (the "
            "Turned on / Skipped recap fields, the skipped-everything "
            "description branch — EssentialSummaryView.render) — outside "
            "the static grammar vocabulary; the override composes the "
            "embed (no golden pins it — the oracle source does)."))


def extras_spec():
    """The extras menu (ExtrasMenuView — ◀ Back, copy verbatim)."""
    from sb.spec.panels import ActionStyle, PanelActionSpec
    from sb.spec.refs import HandlerRef

    return _panel(
        EXTRAS_PANEL_ID, "✨ More you can set up",
        actions=(
            PanelActionSpec(
                action_id="extras_back", label="Back", emoji="◀",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.essential_extras_back")),
        ),
        rows=(("extras_back",),),
        renderer="setup.essential_extras_render",
        justification=(
            "the shipped extras menu carries seven static feature fields "
            "(build_extras_embed) — grammar FieldsBlocks are provider-fed; "
            "the override composes the embed (no golden pins it — the "
            "oracle source does)."))


def resume_spec():
    """The restart-resume bridge (EssentialSetupResumeView — the
    persistent ▶ Resume setup button, static custom_id verbatim)."""
    from sb.spec.panels import ActionStyle, PanelActionSpec
    from sb.spec.refs import HandlerRef

    return _panel(
        RESUME_PANEL_ID, "⏸️ Setup paused",
        actions=(
            PanelActionSpec(
                action_id="resume", label="Resume setup", emoji="▶",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.essential_resume_click"),
                custom_id_override="essential_setup:resume"),
        ),
        rows=(("resume",),),
        renderer="setup.essential_resume_render",
        justification=(
            "the shipped resume prompt is session-parameterized (the "
            "'pick up where you left off (step N)' description over the "
            "persisted essential_step — build_resume_message) — outside "
            "the static grammar vocabulary; the override composes the "
            "embed (no golden pins it — the oracle source does)."))


# --- option providers (the oracle selects' option lists, verbatim) -------------------

def _ensure_providers() -> None:
    from sb.spec.refs import ProviderRef, is_registered, provider

    if is_registered(ProviderRef(_SPAM_OPTIONS_PROVIDER)):
        return

    @provider(_SPAM_OPTIONS_PROVIDER)
    async def spam_options(ctx):
        state = _ctx_flow(ctx)
        return tuple({"label": label, "value": key,
                      "default": key in state.spam_filters}
                     for key, label in _SPAM_FILTERS)

    @provider(_ACTIVITY_OPTIONS_PROVIDER)
    async def activity_options(ctx):
        state = _ctx_flow(ctx)
        options = []
        for flag, label, _default in _ACTIVITY_TYPES:
            entry = {"label": label, "value": flag,
                     "default": flag in state.log_activity}
            if flag == "messages_enabled":
                entry["description"] = ("Shows the content members edited "
                                        "or deleted")
            options.append(entry)
        return tuple(options)

    @provider(_XP_RATE_OPTIONS_PROVIDER)
    async def xp_rate_options(ctx):
        from sb.domain.setup.wizard import XP_RATES

        state = _ctx_flow(ctx)
        return ({"label": "Keep current XP rate", "value": "keep",
                 "default": state.reward_xp_rate == "keep"},
                *({"label": spec[0], "value": key,
                   "default": state.reward_xp_rate == key}
                  for key, spec in XP_RATES.items()))

    @provider(_REWARD_TYPE_OPTIONS_PROVIDER)
    async def reward_type_options(ctx):
        state = _ctx_flow(ctx)
        return tuple({"label": label, "value": key,
                      "default": key in state.reward_types}
                     for key, label in _REWARD_TYPES)

    @provider(_ROLE_SOURCE_OPTIONS_PROVIDER)
    async def role_source_options(ctx):
        state = _ctx_flow(ctx)
        return tuple({"label": label, "value": key,
                      "default": key == state.reward_role_source}
                     for key, label in _ROLE_SOURCES)

    @provider(_ROLE_NAME_OPTIONS_PROVIDER)
    async def role_name_options(ctx):
        state = _ctx_flow(ctx)
        return tuple({"label": name, "value": name,
                      "default": name == state.reward_new_role_name}
                     for name in _SUGGESTED_ROLE_NAMES)

    @provider(_CMD_MODE_OPTIONS_PROVIDER)
    async def cmd_mode_options(ctx):
        state = _ctx_flow(ctx)
        return tuple({"label": label, "value": mode, "description": desc,
                      "default": mode == state.cmd_mode}
                     for mode, label, desc in _CMD_ACCESS_CHOICES)


# --- renderer overrides (the step render() bodies, bytes verbatim) -------------------

def _footer(index: int) -> str:
    return f"Step {index + 1} of {_TOTAL}"


async def _compose(spec, ctx, *, description: str, fields: tuple,
                   footer: str, keep=None, patch=None):
    """Grammar render + the composed embed; ``keep`` filters components
    to the named action/selector ids (run-minted custom_ids are
    ``{panel_id}.{comp_id}``), ``patch`` maps a component id →
    dataclasses.replace kwargs (the state-dependent labels)."""
    import dataclasses

    from sb.kernel.panels.render import RenderedEmbed, render_panel

    base = await render_panel(spec, ctx)
    components = base.components
    if keep is not None:
        allowed = {f"{spec.panel_id}.{name}" for name in keep}
        components = tuple(c for c in components if c.custom_id in allowed)
    if patch:
        patched = []
        for c in components:
            kwargs = patch.get(c.custom_id.removeprefix(f"{spec.panel_id}."))
            if kwargs:
                c = dataclasses.replace(c, **kwargs)
            patched.append(c)
        components = tuple(patched)
    embed = RenderedEmbed(title=spec.title, description=description,
                          fields=fields, footer=footer,
                          style_token="blurple")
    return dataclasses.replace(base, embed=embed, components=components)


async def _render_greet(spec, ctx):
    state = _ctx_flow(ctx)
    chan = (f"<#{state.greet_channel_id}>" if state.greet_channel_id
            else "_not chosen yet_")
    role = f"<@&{state.greet_role_id}>" if state.greet_role_id else "_none_"
    return await _compose(
        spec, ctx,
        description=(
            "Send a friendly message when someone joins, and (if you like) "
            "give every newcomer a role automatically.\n\n"
            "Pick a channel for the welcome message below, then press "
            "**Save & continue**."),
        fields=(("Welcome message channel", chan, False),
                ("Role for newcomers", role, False)),
        footer=_footer(1))


async def _render_mods(spec, ctx):
    state = _ctx_flow(ctx)
    role = (f"<@&{state.mod_role_id}>" if state.mod_role_id
            else "_not chosen yet_")
    return await _compose(
        spec, ctx,
        description=(
            "Choose the role for people who can warn and remove others. "
            "We'll use safe defaults for everything else.\n\n"
            "“Tell members why” sends someone a short note when they're "
            "warned or removed, so they know what happened."),
        fields=(("Moderator role", role, False),
                ("Tell members why", "On" if state.mod_dm_on else "Off",
                 False)),
        footer=_footer(2),
        patch={"mods_dm_toggle": {
            "label": ("Tell members why: ON" if state.mod_dm_on
                      else "Tell members why: OFF"),
            "style": "success" if state.mod_dm_on else "secondary"}})


async def _render_spam(spec, ctx):
    state = _ctx_flow(ctx)
    fields = tuple(
        (label, "On" if key in state.spam_filters else "Off", True)
        for key, label in _SPAM_FILTERS)
    return await _compose(
        spec, ctx,
        description=(
            "Automatically clean up the noise so you don't have to. "
            "Everything is on by default — untick anything you want to "
            "allow, then press **Save & continue**."),
        fields=fields, footer=_footer(3))


def _log_where(channel_id: int | None, default_name: str) -> str:
    if channel_id:
        return f"<#{channel_id}>"
    return f"a new **#{default_name}** channel"


async def _render_log(spec, ctx):
    state = _ctx_flow(ctx)
    fields = [("Moderation log",
               _log_where(state.log_mod_channel_id,
                          state.log_mod_name or _NEW_MOD_CHANNEL_NAME),
               False)]
    if state.log_activity:
        picked = ", ".join(label for flag, label, _ in _ACTIVITY_TYPES
                           if flag in state.log_activity)
        where = _log_where(
            state.log_activity_channel_id,
            state.log_activity_name or _NEW_ACTIVITY_CHANNEL_NAME)
        fields.append(("Activity log", f"{where}\n_Logging: {picked}_",
                       False))
    else:
        fields.append(("Activity log",
                       "_off — tick any activity above to turn it on_",
                       False))
    return await _compose(
        spec, ctx,
        description=(
            "Keep a tidy record of what happens on your server, in two "
            "channels:\n"
            "• a **moderation log** — warnings, timeouts, kicks and bans\n"
            "• an **activity log** — the things you tick below\n\n"
            "Pick a channel for each, or leave one empty and we'll make it "
            f"for you (**#{_NEW_MOD_CHANNEL_NAME}** / "
            f"**#{_NEW_ACTIVITY_CHANNEL_NAME}** — or tap ✏️ to name it). "
            "Then press **Save & continue**."),
        fields=tuple(fields), footer=_footer(4))


async def _render_reward(spec, ctx):
    from sb.domain.setup.wizard import XP_RATES

    state = _ctx_flow(ctx)
    rate = ("Keep current" if state.reward_xp_rate == "keep"
            else XP_RATES[state.reward_xp_rate][0])
    fields = [("XP rate", rate, False)]
    if state.reward_types:
        picked = ", ".join(label for key, label in _REWARD_TYPES
                           if key in state.reward_types)
        fields.append(("Give a reward role", picked, False))
    else:
        fields.append(("Give a reward role", "_off — no role rewards_",
                       False))
    return await _compose(
        spec, ctx,
        description=(
            "Members earn XP as they chat and level up. Choose how fast XP "
            "comes in, and — if you like — give members a role when they "
            "reach a level or stay a while.\n\n"
            "Pick what you want, then press **Next**."),
        fields=tuple(fields), footer=_footer(5),
        patch={"reward_next": {
            "label": "Next" if state.reward_types else "Save & continue"}})


async def _render_reward_role(spec, ctx):
    state = _ctx_flow(ctx)
    if state.reward_role_source == "existing":
        role = (f"<@&{state.reward_existing_role_id}>"
                if state.reward_existing_role_id else "_pick one below_")
    elif state.reward_role_source == "create":
        role = (f"a new **@{state.reward_new_role_name or _DEFAULT_ROLE_NAME}"
                "**")
    else:
        role = f"a new **@{_DEFAULT_ROLE_NAME}**"
    triggers = []
    if "level" in state.reward_types:
        triggers.append(f"at level {_DEFAULT_LEVEL}")
    if "time" in state.reward_types:
        triggers.append(f"after {_DEFAULT_DAYS} days")
    keep = ["reward_source", "reward_save", "reward_role_back",
            "reward_role_skip"]
    if state.reward_role_source == "create":
        keep += ["reward_name", "reward_type_name"]
    elif state.reward_role_source == "existing":
        keep.append("reward_existing")
    return await _compose(
        spec, ctx,
        description=(
            "Which role should members earn?\n"
            "• **Recommended** — we make a fresh **@Regular**\n"
            "• **Create a role I name** — pick a name, we make it\n"
            "• **Use a role I already have** — choose one below"),
        fields=(("Reward role", role, False),
                ("Granted", " and ".join(triggers), False)),
        footer=_footer(5), keep=keep)


async def _render_helpdesk(spec, ctx):
    state = _ctx_flow(ctx)
    staff = (f"<@&{state.helpdesk_staff_role_id}>"
             if state.helpdesk_staff_role_id else "_not chosen yet_")
    log = (f"<#{state.helpdesk_log_channel_id}>"
           if state.helpdesk_log_channel_id else "_none_")
    return await _compose(
        spec, ctx,
        description=(
            "Let members open a private request that only your staff can "
            "see. Pick who should answer them; we set up the rest.\n\n"
            "Then press **Save & continue**."),
        fields=(("Who answers requests", staff, False),
                ("Save chat logs to", log, False)),
        footer=_footer(6))


async def _render_commands(spec, ctx):
    state = _ctx_flow(ctx)
    fields = [("Setting", _CMD_ACCESS_LABELS.get(state.cmd_mode,
                                                 state.cmd_mode), False)]
    keep = ["cmd_mode", "cmd_save", "cmd_back", "cmd_skip"]
    if state.cmd_mode == "selected_channels":
        keep.append("cmd_channels")
        if state.cmd_channel_ids:
            where = ", ".join(f"<#{cid}>" for cid in state.cmd_channel_ids)
        else:
            where = "_pick at least one channel above_"
        fields.append(("Allowed channels", where, False))
    return await _compose(
        spec, ctx,
        description=(
            "Choose where members can use the bot's commands. By default "
            "they work everywhere — you can keep that, limit them to a few "
            "channels, or turn them off for everyone but admins.\n\n"
            "Pick one below, then press **Save & continue**."),
        fields=tuple(fields), footer=_footer(7), keep=keep)


async def _render_summary(spec, ctx):
    import dataclasses

    from sb.kernel.panels.render import RenderedEmbed, render_panel

    state = _ctx_flow(ctx)
    base = await render_panel(spec, ctx)
    description = ("Here's what you switched on. You can change any of it "
                   "later.")
    fields: list[tuple] = []
    if state.applied:
        fields.append(("Turned on",
                       "\n".join(f"• {line}" for line in state.applied),
                       False))
    else:
        description = ("You skipped every step — nothing was changed. "
                       "Run setup again any time.")
    if state.skipped:
        fields.append(("Skipped (you can do these later)",
                       "\n".join(f"• {line}" for line in state.skipped),
                       False))
    fields.append((
        "What next?",
        "✨ **More to set up** — optional extras like a Hall of Fame, "
        "reaction roles, or an AI helper.\n"
        "🔎 **Check my setup** — a quick look at what's on and what isn't.",
        False))
    embed = RenderedEmbed(title="✅ Setup complete", description=description,
                          fields=tuple(fields), style_token="green")
    return dataclasses.replace(base, embed=embed)


async def _render_extras(spec, ctx):
    import dataclasses

    from sb.kernel.panels.render import RenderedEmbed, render_panel

    base = await render_panel(spec, ctx)
    fields = tuple(
        (f"{emoji} {label}", f"{blurb}\nOpen with `{command}`", False)
        for emoji, label, blurb, command in _EXTRAS)
    embed = RenderedEmbed(
        title="✨ More you can set up",
        description=("These are all optional — turn on any that fit your "
                     "server. Run the command shown under each one to set "
                     "it up."),
        fields=fields, style_token="blurple")
    return dataclasses.replace(base, embed=embed)


async def _render_resume(spec, ctx):
    import dataclasses

    from sb.domain.setup import store
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    base = await render_panel(spec, ctx)
    raw_step = None
    try:
        session = await store.get_session_row(int(ctx.guild_id or 0))
        raw_step = session.get("essential_step") if session else None
    except Exception:  # noqa: BLE001 — headless ⇒ the step-1 default
        logger.debug("essential resume: session read failed", exc_info=True)
    human_step = (int(raw_step) if raw_step is not None else 0) + 1
    embed = RenderedEmbed(
        title="⏸️ Setup paused",
        description=(
            "I restarted while you were setting things up, so this wizard "
            "paused for a moment. **Nothing you saved was lost** — each "
            "step is saved the instant you press its button.\n\n"
            f"Click **Resume setup** to pick up where you left off (step "
            f"{human_step})."),
        style_token="blurple")
    return dataclasses.replace(base, embed=embed)


# --- handlers ------------------------------------------------------------------------

def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.essential_back")):
        return

    # ---- shared navigation ----

    @handler("setup.essential_back")
    async def essential_back(req) -> None:
        """The shared _BackButton: one step back (index floor 0)."""
        state = _req_flow(req)
        if state.index > 0:
            state.index -= 1
        await _show_current(req, state)
        return None

    def _skip_handler(title: str):
        async def _skip(req) -> None:
            """_SkipButton — record the step title, advance."""
            await _skip_step(req, _req_flow(req), title)
            return None
        return _skip

    for _slug, _title in (("greet", STEP_TITLES[1]),
                          ("mods", STEP_TITLES[2]),
                          ("spam", STEP_TITLES[3]),
                          ("log", STEP_TITLES[4]),
                          ("reward", STEP_TITLES[5]),
                          ("helpdesk", STEP_TITLES[6]),
                          ("commands", STEP_TITLES[7])):
        handler(f"setup.essential_{_slug}_skip")(_skip_handler(_title))

    # ---- step 2 — greet (GreetMembersStep) ----

    @handler("setup.essential_greet_channel")
    async def greet_channel(req) -> None:
        state = _req_flow(req)
        picked = _picked_int(req)
        if picked is not None:
            state.greet_channel_id = picked
        await _refresh(req)
        return None

    @handler("setup.essential_greet_role")
    async def greet_role(req) -> None:
        state = _req_flow(req)
        state.greet_role_id = _picked_int(req)
        await _refresh(req)
        return None

    @handler("setup.essential_greet_save")
    async def greet_save(req) -> Reply | None:
        state = _req_flow(req)
        if state.greet_channel_id is None:
            # shipped guard copy, verbatim.
            return Reply(BLOCKED,
                         "Pick a **channel** for the welcome message first.")
        try:
            await _set(req, "welcome", "enabled", True)
            await _set(req, "welcome", "join_enabled", True)
            await _bind(req, "welcome", "channel", "channel",
                        state.greet_channel_id)
            if state.greet_role_id is not None:
                await _bind(req, "welcome", "entry_role", "role",
                            state.greet_role_id)
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception("essential setup: greet step apply failed")
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "Something went wrong turning on greetings — "
                         "please try again.")
        line = f"Greetings on, posting in <#{state.greet_channel_id}>"
        if state.greet_role_id is not None:
            line += f" · newcomers get <@&{state.greet_role_id}>"
        await _complete_step(req, state, line)
        return None

    # ---- step 3 — moderators (ModeratorsStep) ----

    @handler("setup.essential_mods_role")
    async def mods_role(req) -> None:
        state = _req_flow(req)
        picked = _picked_int(req)
        if picked is not None:
            state.mod_role_id = picked
        await _refresh(req)
        return None

    @handler("setup.essential_mods_dm_toggle")
    async def mods_dm_toggle(req) -> None:
        state = _req_flow(req)
        state.mod_dm_on = not state.mod_dm_on
        await _refresh(req)
        return None

    @handler("setup.essential_mods_save")
    async def mods_save(req) -> Reply | None:
        state = _req_flow(req)
        if state.mod_role_id is None:
            # shipped guard copy, verbatim.
            return Reply(BLOCKED, "Pick a **moderator role** first.")
        try:
            # the ADR-008 tier grant — this architecture's moderator-role
            # vocabulary (module docstring: the oracle key doesn't exist).
            await _set(req, "governance", "moderator_tier_role_id",
                       int(state.mod_role_id))
            await _set(req, "moderation", "dm_on_action", state.mod_dm_on)
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception("essential setup: moderators step apply failed")
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "Something went wrong saving your moderators — "
                         "please try again.")
        await _complete_step(
            req, state,
            f"Moderator role set to <@&{state.mod_role_id}>"
            + (" · members told why" if state.mod_dm_on else ""))
        return None

    # ---- step 4 — spam (BlockSpamStep) ----

    @handler("setup.essential_spam_pick")
    async def spam_pick(req) -> None:
        state = _req_flow(req)
        state.spam_filters = {str(v)
                              for v in (req.args.get("values", ()) or ())}
        await _refresh(req)
        return None

    @handler("setup.essential_spam_save")
    async def spam_save(req) -> Reply | None:
        state = _req_flow(req)
        try:
            await _set(req, "automod", "enabled", True)
            for key, _label in _SPAM_FILTERS:
                await _set(req, "automod", key, key in state.spam_filters)
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception("essential setup: block-spam step apply failed")
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "Something went wrong turning on protection — "
                         "please try again.")
        on_labels = [label for key, label in _SPAM_FILTERS
                     if key in state.spam_filters]
        line = "Spam protection on"
        if on_labels:
            line += " · " + ", ".join(on_labels).lower()
        await _complete_step(req, state, line)
        return None

    # ---- step 5 — log channels (LogChannelStep) ----

    @handler("setup.essential_log_activity")
    async def log_activity(req) -> None:
        state = _req_flow(req)
        state.log_activity = {str(v)
                              for v in (req.args.get("values", ()) or ())}
        await _refresh(req)
        return None

    @handler("setup.essential_log_mod_pick")
    async def log_mod_pick(req) -> None:
        state = _req_flow(req)
        state.log_mod_channel_id = _picked_int(req)
        await _refresh(req)
        return None

    @handler("setup.essential_log_activity_pick")
    async def log_activity_pick(req) -> None:
        state = _req_flow(req)
        state.log_activity_channel_id = _picked_int(req)
        await _refresh(req)
        return None

    @handler("setup.essential_log_names")
    async def log_names(req) -> None:
        """_ChannelNamesModal.on_submit: stash the typed names."""
        state = _req_flow(req)
        state.log_mod_name = (str(req.args.get("mod_name") or "").strip()
                              or None)
        state.log_activity_name = (
            str(req.args.get("activity_name") or "").strip() or None)
        await _refresh(req)
        return None

    @handler("setup.essential_log_save")
    async def log_save(req) -> Reply | None:
        state = _req_flow(req)
        created: list[str] = []
        mod_name = state.log_mod_name or _NEW_MOD_CHANNEL_NAME
        activity_name = (state.log_activity_name
                         or _NEW_ACTIVITY_CHANNEL_NAME)
        mod_id = state.log_mod_channel_id
        if mod_id is None:
            mod_id = await _create_channel(req, mod_name)
            if mod_id is None:
                # shipped copy, verbatim.
                return Reply(BLOCKED,
                             "Couldn't make a channel — please pick "
                             "existing ones instead.")
            created.append(mod_name)
        activity_id: int | None = None
        if state.log_activity:
            activity_id = state.log_activity_channel_id
            if activity_id is None:
                activity_id = await _create_channel(req, activity_name)
                if activity_id is None:
                    return Reply(BLOCKED,
                                 "Couldn't make a channel — please pick "
                                 "existing ones instead.")
                created.append(activity_name)
        try:
            await _set(req, "logging", "enabled", True)
            await _bind(req, "logging", "mod_channel", "channel", mod_id)
            for flag, _label, _default in _ACTIVITY_TYPES:
                await _set(req, "logging", flag, flag in state.log_activity)
            if activity_id is not None:
                await _bind(req, "logging", "events_channel", "channel",
                            activity_id)
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception(
                "essential setup: log-channel step apply failed")
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "Something went wrong saving your log channels — "
                         "please try again.")
        parts = [f"moderation → <#{mod_id}>"]
        if activity_id is not None:
            picked = ", ".join(label for flag, label, _ in _ACTIVITY_TYPES
                               if flag in state.log_activity).lower()
            parts.append(f"activity ({picked}) → <#{activity_id}>")
        line = "Logging on · " + " · ".join(parts)
        if created:
            line += " · created " + ", ".join(f"#{n}" for n in created)
        await _complete_step(req, state, line)
        return None

    # ---- step 6 — rewards (RewardActivityStep) ----

    @handler("setup.essential_reward_rate")
    async def reward_rate(req) -> None:
        state = _req_flow(req)
        values = tuple(req.args.get("values", ()) or ())
        if values:
            state.reward_xp_rate = str(values[0])
        await _refresh(req)
        return None

    @handler("setup.essential_reward_types")
    async def reward_types(req) -> None:
        state = _req_flow(req)
        state.reward_types = {str(v)
                              for v in (req.args.get("values", ()) or ())}
        await _refresh(req)
        return None

    async def _apply_rewards_and_complete(req, state: EssentialFlow, *,
                                          role_id: int | None,
                                          role_name: str | None,
                                          created: bool) -> Reply | None:
        from sb.domain.setup.wizard import XP_RATES
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        try:
            if state.reward_xp_rate != "keep":
                _label, xp_min, xp_max, cooldown = XP_RATES[
                    state.reward_xp_rate]
                await _set(req, "xp", "xp_min", xp_min)
                await _set(req, "xp", "xp_max", xp_max)
                await _set(req, "xp", "xp_cooldown", cooldown)
            if state.reward_types and role_id is not None \
                    and role_name is not None:
                # ONE full-row threshold upsert carrying both triggers
                # (module docstring: the K7 leg overwrites the whole row,
                # so the oracle's two per-column writes fold into one).
                result = await engine.run(
                    WorkflowRef("role.set_threshold"),
                    ctx_from_request(req, {
                        "role_name": role_name,
                        "display_name": role_name,
                        "role_id": int(role_id),
                        "days_required": (_DEFAULT_DAYS
                                          if "time" in state.reward_types
                                          else 0),
                        "level_required": (_DEFAULT_LEVEL
                                           if "level" in state.reward_types
                                           else None),
                        "xp_auto_assign": "level" in state.reward_types,
                    }))
                if result.outcome != SUCCESS:
                    raise RuntimeError(
                        f"role.set_threshold → {result.outcome}")
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception("essential setup: reward step apply failed")
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "Something went wrong saving rewards — please try "
                         "again.")
        parts: list[str] = []
        if state.reward_xp_rate != "keep":
            parts.append(
                "XP rate "
                + XP_RATES[state.reward_xp_rate][0].split(" — ")[0].lower())
        if state.reward_types and role_id is not None:
            triggers = []
            if "level" in state.reward_types:
                triggers.append(f"level {_DEFAULT_LEVEL}")
            if "time" in state.reward_types:
                triggers.append(f"{_DEFAULT_DAYS} days")
            verb = "new role" if created else "role"
            parts.append(f"{verb} <@&{role_id}> at {' / '.join(triggers)}")
        line = ("Rewards: no changes" if not parts
                else "Rewards on · " + " · ".join(parts))
        state.reward_phase = "config"
        await _complete_step(req, state, line)
        return None

    @handler("setup.essential_reward_next")
    async def reward_next(req) -> Reply | None:
        """Screen 1's 🏅 button (``on_next``): no rewards → apply the XP
        rate and finish; otherwise swap to the roles screen."""
        state = _req_flow(req)
        if not state.reward_types:
            return await _apply_rewards_and_complete(
                req, state, role_id=None, role_name=None, created=False)
        state.reward_phase = "roles"
        from sb.domain.setup.wizard import _open

        await _open(req, REWARD_ROLE_PANEL_ID)
        return None

    @handler("setup.essential_reward_back")
    async def reward_back(req) -> None:
        """Screen 2 "Back" returns to screen 1 (the oracle go_back
        override); screen 1's Back leaves the step (the shared handler)."""
        state = _req_flow(req)
        state.reward_phase = "config"
        from sb.domain.setup.wizard import _open

        await _open(req, REWARD_PANEL_ID)
        return None

    @handler("setup.essential_reward_source")
    async def reward_source(req) -> None:
        state = _req_flow(req)
        values = tuple(req.args.get("values", ()) or ())
        if values:
            state.reward_role_source = str(values[0])
        await _refresh(req)
        return None

    @handler("setup.essential_reward_name")
    async def reward_name(req) -> None:
        state = _req_flow(req)
        values = tuple(req.args.get("values", ()) or ())
        if values:
            state.reward_new_role_name = str(values[0])
        await _refresh(req)
        return None

    @handler("setup.essential_reward_existing")
    async def reward_existing(req) -> None:
        state = _req_flow(req)
        picked = _picked_int(req)
        state.reward_existing_role_id = picked
        state.reward_existing_role_name = (str(picked) if picked is not None
                                           else None)
        await _refresh(req)
        return None

    @handler("setup.essential_reward_typed_name")
    async def reward_typed_name(req) -> None:
        """_RoleNameModal.on_submit: stash the typed name + flip the
        source to create (the oracle body)."""
        state = _req_flow(req)
        state.reward_new_role_name = (
            str(req.args.get("role_name") or "").strip() or None)
        state.reward_role_source = "create"
        await _refresh(req)
        return None

    @handler("setup.essential_reward_save")
    async def reward_save(req) -> Reply | None:
        """Screen 2 Save: resolve the reward role, then apply."""
        state = _req_flow(req)
        if state.reward_role_source == "existing":
            if state.reward_existing_role_id is None:
                # shipped copy, verbatim.
                return Reply(BLOCKED,
                             "Pick a role to grant, or switch to "
                             "**Recommended** to make one.")
            role_id = state.reward_existing_role_id
            role_name = (state.reward_existing_role_name
                         or str(state.reward_existing_role_id))
            created = False
        else:
            name = (state.reward_new_role_name
                    if state.reward_role_source == "create"
                    and state.reward_new_role_name
                    else _DEFAULT_ROLE_NAME)
            created_id = await _create_role(req, name)
            if created_id is None:
                # shipped copy, verbatim.
                return Reply(BLOCKED,
                             "Couldn't make the role — please reuse an "
                             "existing one instead.")
            role_id, role_name, created = created_id, name, True
        return await _apply_rewards_and_complete(
            req, state, role_id=role_id, role_name=role_name,
            created=created)

    # ---- step 7 — help desk (HelpDeskStep) ----

    @handler("setup.essential_helpdesk_staff")
    async def helpdesk_staff(req) -> None:
        state = _req_flow(req)
        picked = _picked_int(req)
        if picked is not None:
            state.helpdesk_staff_role_id = picked
        await _refresh(req)
        return None

    @handler("setup.essential_helpdesk_log")
    async def helpdesk_log(req) -> None:
        state = _req_flow(req)
        picked = _picked_int(req)
        if picked is not None:
            state.helpdesk_log_channel_id = picked
        await _refresh(req)
        return None

    @handler("setup.essential_helpdesk_save")
    async def helpdesk_save(req) -> Reply | None:
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        state = _req_flow(req)
        if state.helpdesk_staff_role_id is None:
            # shipped guard copy, verbatim.
            return Reply(BLOCKED,
                         "Pick a **staff role** first — it's who can see "
                         "and answer requests.")
        try:
            result = await engine.run(
                WorkflowRef("ticket.update_config"),
                ctx_from_request(req, {
                    "enabled": True,
                    "staff_role_id": int(state.helpdesk_staff_role_id),
                    "log_channel_id": state.helpdesk_log_channel_id}))
            if result.outcome != SUCCESS:
                raise RuntimeError(f"ticket.update_config → {result.outcome}")
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception("essential setup: help-desk step apply failed")
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "Something went wrong setting up the help desk — "
                         "please try again.")
        await _complete_step(
            req, state,
            f"Help desk on, answered by <@&{state.helpdesk_staff_role_id}>")
        return None

    # ---- step 8 — command access (CommandChannelsStep) ----

    @handler("setup.essential_commands_mode")
    async def commands_mode(req) -> None:
        state = _req_flow(req)
        values = tuple(req.args.get("values", ()) or ())
        if values:
            state.cmd_mode = str(values[0])
        await _refresh(req)
        return None

    @handler("setup.essential_commands_channels")
    async def commands_channels(req) -> None:
        state = _req_flow(req)
        state.cmd_channel_ids = [
            int(v) for v in (req.args.get("values", ()) or ())
            if str(v).isdigit()]
        await _refresh(req)
        return None

    @handler("setup.essential_commands_save")
    async def commands_save(req) -> Reply | None:
        from sb.domain.platform import command_access

        state = _req_flow(req)
        if state.cmd_mode == "selected_channels" \
                and not state.cmd_channel_ids:
            # shipped guard copy, verbatim.
            return Reply(BLOCKED,
                         "Pick at least one channel where commands should "
                         "work — or choose **Anywhere on the server**.")
        try:
            result = await command_access.set_access_mode(
                ctx_from_request(req, {}), mode=state.cmd_mode)
            if getattr(result, "outcome", None) != SUCCESS:
                raise RuntimeError(
                    f"platform.set_access_mode → "
                    f"{getattr(result, 'outcome', None)}")
            if state.cmd_mode == "selected_channels":
                result = await command_access.set_access_channels(
                    ctx_from_request(req, {}),
                    channel_ids=tuple(state.cmd_channel_ids))
                if getattr(result, "outcome", None) != SUCCESS:
                    raise RuntimeError(
                        f"platform.set_access_channels → "
                        f"{getattr(result, 'outcome', None)}")
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception(
                "essential setup: command-channels step apply failed")
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "Something went wrong saving where commands work — "
                         "please try again.")
        if state.cmd_mode == "selected_channels":
            count = len(state.cmd_channel_ids)
            line = (f"Commands limited to <#{state.cmd_channel_ids[0]}>"
                    if count == 1 else f"Commands limited to {count} "
                                       "channels")
        elif state.cmd_mode == "disabled_except_bootstrap":
            line = "Commands off for members (admins keep access)"
        else:
            line = "Commands available in every channel"
        await _complete_step(req, state, line)
        return None

    # ---- the summary + extras (EssentialSummaryView / ExtrasMenuView) ----

    @handler("setup.essential_summary_done")
    async def summary_done(req) -> Reply:
        """✅ All done — the oracle disabled the view's buttons; the
        component model keeps no per-message disable lane on refresh, so
        the terminal answers as a text reply carrying the summary
        headline (module docstring, the ledgered seam)."""
        state = _req_flow(req)
        if state.applied:
            return Reply(SUCCESS,
                         "✅ Setup complete — here's what you switched on. "
                         "You can change any of it later.")
        return Reply(SUCCESS,
                     "You skipped every step — nothing was changed. Run "
                     "setup again any time.")

    @handler("setup.essential_summary_extras")
    async def summary_extras(req) -> None:
        from sb.domain.setup.wizard import _open

        await _open(req, EXTRAS_PANEL_ID)
        return None

    @handler("setup.essential_summary_check")
    async def summary_check(req) -> Reply:
        """🔎 Check my setup — the plain-language health check (the
        oracle's ephemeral embed, carried as the text-reply seam)."""
        return Reply(SUCCESS,
                     await build_check_setup_text(int(req.guild_id or 0)))

    @handler("setup.essential_extras_back")
    async def extras_back(req) -> None:
        from sb.domain.setup.wizard import _open

        await _open(req, SUMMARY_PANEL_ID)
        return None

    # ---- the restart-resume lane (EssentialSetupResumeView) ----

    @handler("setup.essential_resume_click")
    async def resume_click(req) -> Reply | None:
        """▶ Resume setup: gate, rebuild the flow at the saved step
        (clamped defensively — the oracle body), land on its card."""
        from sb.domain.setup import store, wizard

        if not await wizard.can_apply_setup(req):
            # shipped refusal copy, verbatim (the ported gate ladder —
            # module docstring).
            return Reply(BLOCKED, _RESUME_GATE_MSG)
        state = _req_flow(req)
        try:
            session = await store.get_session_row(int(req.guild_id or 0))
        except Exception:  # noqa: BLE001 — the oracle resume-failed branch
            logger.exception("essential_setup resume: resume_session failed")
            session = None
        step = session.get("essential_step") if session else None
        if step is not None:
            state.index = max(0, min(int(step), state.total))
        await _show_current(req, state)
        return None


# --- registration ---------------------------------------------------------------------

_PANEL_FACTORIES = (
    (GREET_PANEL_ID, greet_spec),
    (MODS_PANEL_ID, mods_spec),
    (SPAM_PANEL_ID, spam_spec),
    (LOG_PANEL_ID, log_spec),
    (REWARD_PANEL_ID, reward_spec),
    (REWARD_ROLE_PANEL_ID, reward_role_spec),
    (HELPDESK_PANEL_ID, helpdesk_spec),
    (COMMANDS_PANEL_ID, commands_spec),
    (SUMMARY_PANEL_ID, summary_spec),
    (EXTRAS_PANEL_ID, extras_spec),
    (RESUME_PANEL_ID, resume_spec),
)

_RENDERERS = (
    ("setup.essential_greet_render", _render_greet),
    ("setup.essential_mods_render", _render_mods),
    ("setup.essential_spam_render", _render_spam),
    ("setup.essential_log_render", _render_log),
    ("setup.essential_reward_render", _render_reward),
    ("setup.essential_reward_role_render", _render_reward_role),
    ("setup.essential_helpdesk_render", _render_helpdesk),
    ("setup.essential_commands_render", _render_commands),
    ("setup.essential_summary_render", _render_summary),
    ("setup.essential_extras_render", _render_extras),
    ("setup.essential_resume_render", _render_resume),
)


def _register_panels() -> None:
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    for name, fn in _RENDERERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)
    for pid, factory in _PANEL_FACTORIES:
        if not is_registered(PanelRef(pid)):
            panel(pid)(factory)


_ensure_providers()
_register()
_register_panels()


def ensure_essential_steps_refs() -> None:
    _ensure_providers()
    _register()
    _register_panels()

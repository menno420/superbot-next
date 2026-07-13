"""The setup wizard INTERIOR (the wizard-lifecycle slice, ORDER 017) —
the click lanes behind the four golden-pinned setup cards, ported from
the oracle (menno420/superbot):

* the DEPTH CHOOSER's three buttons (views/setup/depth_panel.py
  ``DepthPanelView._select``): persist the choice through the K7
  ``setup.set_depth`` op, then land on the sections hub at that depth;
* the SECTIONS HUB (views/setup/hub.py ``SetupHubView`` +
  ``build_hub_embed``) — the depth click's shipped destination — with
  its Change-depth navigation live and each section button an honest
  named-successor terminal (the section-flows slice);
* the ESSENTIAL Step-1 card's interior (views/setup/essential_setup.py
  ``ServerTypeStep``): the five-kind select records the pick, Save &
  continue applies the shipped starter-set bundle FOR REAL through the
  audited K7 ``settings.set_scalar`` lane (the oracle's
  SettingsMutationPipeline twin) and advances into the guided spine,
  Skip records the step and moves on — steps 2–8, the summary and the
  restart-resume lane are LIVE (the essential-steps slice —
  sb/domain/setup/essential_steps.py);
* the SMART-SUGGESTIONS review lanes (views/setup/ai_review/
  main_panel.py + per_recommendation.py): accept-all / reject-AI /
  rerun mutate the in-memory review state exactly like the oracle's
  ``AcceptedSet`` (its own docstring: "No DB writes … only mutates the
  in-memory AcceptedSet"), Review-one-by-one walks the per-suggestion
  card, and Stage writes the accepted set into the K9 draft lane
  (producer ``human_setup``) — the oracle's
  ``setup_draft.replace_recommended_for_section`` sole-writer twin.

NO GOLDEN drives a click on any of these components (panels.py module
pin), so the oracle SOURCES pin the copy; every golden-pinned OPEN
render stays byte-identical.

Presentation divergence, ledgered: the oracle swapped views in place
via ``edit_message``; this architecture's navigation lane opens the
destination panel through ``open_panel`` (the #295 settings-hub
precedent) and refreshes a panel's OWN card in place via
``refresh_session_view``.

The FINAL-REVIEW APPLY LANE is LIVE (the final-review slice —
sb/domain/setup/final_review.py): the ``final_review`` section button
lands on the ported FinalReviewView card, Apply executes the staged
ops through the K9 DraftPipeline over the audited K7 seams, and the
apply-summary / partial-recovery / setup-complete views ride along.

The per-suggestion EDIT lane is LIVE (the suggestion-edit slice): a
``create`` suggestion's Edit opens the "Edit suggestion" rename modal
(G-10 form; submit rewrites the draft row + re-accepts it and
advances — the oracle ``apply_edit``/``_swap_and_accept``), a ``bind``
suggestion's Edit answers the shipped can't-re-pick explanation (the
native ChannelSelect/RoleSelect re-pick sub-view — oracle
``_RepickTargetView`` — is the flagged follow-up), and the staged
``bind_channel`` payload carries ``target_name`` so the (possibly
edited) name round-trips into the final-review pending line.

The SECTION-FLOW SPINE + the first two per-section flows are LIVE (the
section-flows slice — sb/domain/setup/section_card.py carries the
shared card frame, the setup_progress status vocabulary and the
replace-recommended/stage-custom/skip staging seams;
sb/domain/setup/wizard_nav.py carries the LINEAR WIZARD STEPS behind
↩ Back to wizard — ``setup.back_to_wizard`` is live there;
sb/domain/setup/preset_select.py flips
``setup.open_section_preset_select`` — pick → preview → stage-every-op
into the K9 draft; sb/domain/setup/channels.py flips
``setup.open_section_channels`` — the declared-binding walk, the
channel pick staging ``bind_channel``, and the high-confidence
Apply-Recommended builder).

The SETTINGS-WRITE section flows are LIVE (the settings-write slice):
sb/domain/setup/logging_presets.py flips
``setup.open_section_logging_presets`` — the Single / Balanced /
Detailed / Custom picker staging ``create_channel`` rows (fail-closed
op kind, its module-docstring ledger); sb/domain/setup/moderation.py
flips ``setup.open_section_moderation`` — the four-knob detail view
staging ``set_setting`` rows through the registered
``settings.set_scalar`` op kind; sb/domain/setup/cleanup.py flips
``setup.open_section_cleanup`` — the scope × level walker + the
six-profile batch picker staging ``set_cleanup_policy`` through the
newly registered K7 ``governance.set_cleanup`` op.

The ROLES-FAMILY section flows are LIVE (the roles-family slice):
sb/domain/setup/roles.py flips ``setup.open_section_roles`` — the
time/XP tier detail staging ``set_role_threshold`` rows through the
newly registered K7 ``role.set_threshold`` op (time + XP folded per
role onto the full-row-upsert leg, its module-docstring ledger);
sb/domain/setup/role_templates.py flips
``setup.open_section_role_templates`` — the six-template
permission-free bundle catalogue (pick → preview → stage), each
missing role staging a ``create_managed_role`` row (fail-closed op
kind, the logging_presets ``create_channel`` precedent).

Named successors kept honest (each a declared BLOCKED terminal, never
silent): the remaining TWO per-section flows — cog_routing · ticket
(the final section-flow slice closes the lane).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = [
    "SECTION_DEPTHS",
    "SERVER_TYPES",
    "XP_RATES",
    "ReviewState",
    "can_apply_setup",
    "ensure_wizard_refs",
    "essential_pick",
    "review_state",
    "reset_wizard_state_for_tests",
    "sections_for_depth",
    "staged_ops_count",
]

logger = logging.getLogger("sb.domain.setup")


# --- shipped data, verbatim ----------------------------------------------------------

#: XP rate presets (essential_setup.py ``_XP_RATES``): key → (label,
#: xp_min, xp_max, cooldown_seconds). "standard" mirrors the schema
#: defaults (15/25/60).
XP_RATES: dict[str, tuple[str, int, int, int]] = {
    "relaxed": ("Relaxed — slower leveling", 10, 15, 120),
    "standard": ("Standard — balanced", 15, 25, 60),
    "active": ("Active — faster leveling", 20, 40, 30),
}


@dataclass(frozen=True)
class _ServerTypePreset:
    """One server-type starter set (essential_setup.py
    ``_ServerTypePreset``) — a bundle of safe, reversible settings."""

    key: str
    label: str
    emoji: str
    blurb: str
    settings: tuple[tuple[str, str, object], ...]
    xp_rate: str | None = None


#: the five starter sets (essential_setup.py ``_SERVER_TYPES``,
#: verbatim — every value a channel-independent boolean/scalar; picking
#: a type never creates or binds anything).
SERVER_TYPES: tuple[_ServerTypePreset, ...] = (
    _ServerTypePreset(
        key="community", label="Community", emoji="💬",
        blurb="balanced spam protection, members told why they're "
              "actioned, steady XP",
        settings=(
            ("automod", "enabled", True),
            ("automod", "spam_enabled", True),
            ("automod", "invites_enabled", True),
            ("automod", "caps_enabled", False),
            ("automod", "mentions_enabled", True),
            ("moderation", "dm_on_action", True),
        ),
        xp_rate="standard"),
    _ServerTypePreset(
        key="gaming", label="Gaming", emoji="🎮",
        blurb="spam & mass-ping protection (invite links allowed), "
              "faster XP",
        settings=(
            ("automod", "enabled", True),
            ("automod", "spam_enabled", True),
            ("automod", "invites_enabled", False),
            ("automod", "caps_enabled", False),
            ("automod", "mentions_enabled", True),
            ("moderation", "dm_on_action", True),
        ),
        xp_rate="active"),
    _ServerTypePreset(
        key="support", label="Support / Help desk", emoji="🛟",
        blurb="strict protection on everything, members told why, "
              "relaxed XP",
        settings=(
            ("automod", "enabled", True),
            ("automod", "spam_enabled", True),
            ("automod", "invites_enabled", True),
            ("automod", "caps_enabled", True),
            ("automod", "mentions_enabled", True),
            ("moderation", "dm_on_action", True),
        ),
        xp_rate="relaxed"),
    _ServerTypePreset(
        key="creator", label="Creator / Content", emoji="🎨",
        blurb="balanced spam protection, members told why, steady XP",
        settings=(
            ("automod", "enabled", True),
            ("automod", "spam_enabled", True),
            ("automod", "invites_enabled", True),
            ("automod", "caps_enabled", False),
            ("automod", "mentions_enabled", True),
            ("moderation", "dm_on_action", True),
        ),
        xp_rate="standard"),
    _ServerTypePreset(
        key="exploring", label="Just exploring", emoji="🧭",
        blurb="just basic spam protection — set everything else up "
              "yourself",
        settings=(
            ("automod", "enabled", True),
            ("automod", "spam_enabled", True),
        ),
        xp_rate=None),
)


def server_type(key: str) -> _ServerTypePreset | None:
    for preset in SERVER_TYPES:
        if preset.key == key:
            return preset
    return None


#: per-section depth participation (the oracle ``SetupSection.depths``
#: values, verbatim per views/setup/sections/*.py; the default —
#: preset_select, channels, logging_presets, final_review — is all
#: three). Carried as data because the ported ``WizardSectionSpec``
#: deliberately has no depths facet (band 1 kept slug/label/emoji/
#: order/op_kinds).
SECTION_DEPTHS: dict[str, frozenset[str]] = {
    "preset_select": frozenset({"quick", "standard", "advanced"}),
    "channels": frozenset({"quick", "standard", "advanced"}),
    "logging_presets": frozenset({"quick", "standard", "advanced"}),
    "roles": frozenset({"standard", "advanced"}),
    "role_templates": frozenset({"standard", "advanced"}),
    "cleanup": frozenset({"advanced"}),
    "moderation": frozenset({"standard", "advanced"}),
    "cog_routing": frozenset({"advanced"}),
    "ticket": frozenset({"standard", "advanced"}),
    "final_review": frozenset({"quick", "standard", "advanced"}),
}


def sections_for_depth(depth: str | None):
    """The shipped ``REGISTRY.for_depth`` filter: ``None`` (no choice
    persisted yet) returns every section so the hub is never empty."""
    from sb.domain.setup.sections import REGISTRY, register_shipped_sections

    register_shipped_sections()
    ordered = REGISTRY.ordered()
    if depth is None:
        return ordered
    return tuple(s for s in ordered
                 if depth in SECTION_DEPTHS.get(s.slug, frozenset()))


# --- in-memory interior state (the oracle's view-held state, ported) ------------------

#: the essential Step-1 pick (the oracle held it on ``ServerTypeStep``;
#: author-bound, per guild — restart forgets it exactly like the
#: oracle's in-memory view did).
_ESSENTIAL_PICKS: dict[str, str] = {}


@dataclass
class ReviewState:
    """The oracle ``AIReviewPanelView`` state: the active draft + the
    ``AcceptedSet`` + the last-action footer + the walkthrough index."""

    draft: object
    accepted: list = field(default_factory=list)
    last_status: str | None = None
    index: int = 0

    # -- the AcceptedSet port (main_panel.AcceptedSet, verbatim keys) --
    def add(self, rec) -> bool:
        key = (rec.subsystem, rec.binding_name)
        if any((r.subsystem, r.binding_name) == key for r in self.accepted):
            return False
        self.accepted.append(rec)
        return True

    def add_many(self, recs) -> int:
        return sum(1 for rec in recs if self.add(rec))

    def remove(self, subsystem: str, binding_name: str) -> bool:
        for i, rec in enumerate(self.accepted):
            if rec.subsystem == subsystem and rec.binding_name == binding_name:
                del self.accepted[i]
                return True
        return False

    def contains(self, rec) -> bool:
        return any((r.subsystem, r.binding_name)
                   == (rec.subsystem, rec.binding_name)
                   for r in self.accepted)

    @property
    def count(self) -> int:
        return len(self.accepted)


_REVIEW: dict[str, ReviewState] = {}


def _state_key(guild_id: int, user_id: int) -> str:
    return f"{int(guild_id)}:{int(user_id)}"


def essential_pick(guild_id: int, user_id: int) -> str | None:
    return _ESSENTIAL_PICKS.get(_state_key(guild_id, user_id))


def set_essential_pick(guild_id: int, user_id: int, kind: str) -> None:
    _ESSENTIAL_PICKS[_state_key(guild_id, user_id)] = kind


def seed_review_state(guild_id: int, user_id: int, draft) -> ReviewState:
    state = ReviewState(draft=draft)
    _REVIEW[_state_key(guild_id, user_id)] = state
    return state


async def review_state(guild_id: int, user_id: int) -> ReviewState:
    """The click lanes' state read; a missing entry (process restart)
    re-derives the draft through the DETERMINISTIC advisor — the same
    reproducible run ``/setup-describe`` took (the AI lane is key-gated
    off in this build, the shipped build_advisor fallback)."""
    state = _REVIEW.get(_state_key(guild_id, user_id))
    if state is None:
        from sb.domain.setup import plan

        draft = await plan.suggest(int(guild_id))
        state = seed_review_state(guild_id, user_id, draft)
    return state


def reset_wizard_state_for_tests() -> None:
    _ESSENTIAL_PICKS.clear()
    _REVIEW.clear()
    try:
        from sb.domain.setup.essential_steps import (
            reset_essential_state_for_tests,
        )

        reset_essential_state_for_tests()
    except ImportError:  # pragma: no cover — module always ships alongside
        pass


# --- the apply-authority gate (setup_access.can_apply_setup, ported) ------------------

async def can_apply_setup(req) -> bool:
    """The shipped ``setup_access.can_apply_setup`` ladder over raw ids
    (its ``can_apply_setup_by_id`` twin): platform owner OR server owner
    OR delegated setup admin — administrators without delegation stay
    read-only (the owner keeps control of capability-significant
    changes). Owner id comes from the session row when one exists, else
    the guild directory (the same read the entries use)."""
    from sb.kernel.authority.owner import is_platform_owner

    user_id = int(getattr(req.actor, "user_id", 0) or 0)
    if is_platform_owner(user_id):
        return True
    from sb.domain.setup import store

    guild_id = int(req.guild_id or 0)
    try:
        session = await store.get_session_row(guild_id)
    except Exception:  # noqa: BLE001 — FAIL CLOSED: an unreadable session
        logger.exception("setup wizard: session read failed in gate")
        session = None  # never widens access — the owner ladder still runs
    delegated = tuple(session.get("delegated_admins") or ()) if session else ()
    if user_id in {int(d) for d in delegated}:
        return True
    owner_id = int(session["owner_id"]) if session and session.get("owner_id") else 0
    if not owner_id:
        try:
            from sb.domain.utility.service import guild_directory

            info = await guild_directory().guild_info(guild_id)
            owner_id = int(info.owner_id)
        except Exception:  # noqa: BLE001 — headless directory ⇒ no owner read
            owner_id = 0
    return bool(owner_id) and user_id == owner_id


#: shipped gate refusals, verbatim (hub.SetupHubView._gate_apply ·
#: main_panel._stage_final · cogs/setup_cog._toggle_skip / reset).
GATE_MSG_WIZARD = ("Only the server owner or a delegated setup admin can run "
                   "the wizard. Ask the server owner to grant you "
                   "`/setup-delegate`.")
GATE_MSG_STAGE = ("Only the server owner or a delegated setup admin can stage "
                  "setup operations. Ask the owner to grant you "
                  "`/setup-delegate`.")
GATE_MSG_SKIP = ("Only the server owner or a delegated setup admin can "
                 "change a section's skipped state.")
GATE_MSG_RESET = ("Only the server owner or a delegated setup admin can "
                  "reset staged setup operations.")


# --- the K9 staging lane (setup_draft.replace_recommended_for_section, ported) --------

#: the staged-suggestion label prefix (main_panel._stage_final's
#: ``f"[suggestions] {op.subsystem}.{op.kind}"`` labels — the section
#: provenance the replace matcher keys on).
_SUGGESTIONS_LABEL_PREFIX = "[suggestions] "

_BIND_CHANNEL_OP_KIND = "bind_channel"


def _register_op_kind() -> None:
    """Bind the ONE op kind the deterministic advisor's recommendations
    stage (``bind_channel`` — the G-19 section vocabulary's channel-bind
    entry) onto the audited K7 ``settings.bind`` op, so the K9 pipeline's
    fail-closed registry accepts the staged rows. The final-review APPLY
    lane (final_review.py) executes them through the same registry;
    staging itself only ever writes draft rows."""
    from sb.kernel.draft.registry import OP_KINDS, OpKindBinding
    from sb.spec.events import FieldSpec
    from sb.spec.refs import WorkflowRef

    binding = OpKindBinding(
        op_kind=_BIND_CHANNEL_OP_KIND,
        workflow_ref=WorkflowRef("settings.bind"),
        payload_schema=(FieldSpec("subsystem", "str"),
                        FieldSpec("name", "str"),
                        FieldSpec("kind", "str"),
                        FieldSpec("resource_id", "int")),
        is_resource_create=False)
    try:
        OP_KINDS.register(binding)
    except ValueError as exc:
        if "bound twice" not in str(exc):
            raise


def _guild_scope(guild_id: int):
    """The per-GUILD draft scope — the oracle setup draft was keyed on
    the guild alone (``setup_draft.list_ops(guild_id)``); actor
    accountability rides the audit rows + op labels, not the scope."""
    from sb.spec.draft import OwnerScope

    return OwnerScope(guild_id=int(guild_id), actor_id=None)


async def _open_guild_drafts(guild_id: int):
    from sb.kernel.draft.store import DraftStore

    return await DraftStore().list_open(_guild_scope(guild_id))


async def staged_ops_count(guild_id: int) -> int:
    """The oracle ``setup_draft.count`` read (the ``/setup-reset`` and
    hub pending-ops feed)."""
    drafts = await _open_guild_drafts(int(guild_id))
    return sum(len(d.operations) for d in drafts)


async def stage_accepted(guild_id: int, accepted: list) -> int:
    """The oracle ``replace_recommended_for_section(guild_id,
    "suggestions", ops, …)`` semantics over the K9 store: drop the
    previously staged ``[suggestions]`` rows, append the accepted set as
    ``bind_channel`` operations. Returns the staged count."""
    from sb.kernel.draft.store import DraftStore
    from sb.spec.draft import DraftOperation, Producer

    _register_op_kind()
    store = DraftStore()
    drafts = await _open_guild_drafts(guild_id)
    if drafts:
        draft = drafts[0]
        for op in draft.operations:
            if op.label.startswith(_SUGGESTIONS_LABEL_PREFIX):
                await store.remove(draft.draft_id, op.op_seq)
    else:
        draft = await store.create(producer=Producer.HUMAN_SETUP,
                                   owner_scope=_guild_scope(guild_id))
    staged = 0
    for rec in accepted:
        await store.add(draft.draft_id, DraftOperation(
            op_seq=0,   # append_operation assigns the real sequence
            op_kind=_BIND_CHANNEL_OP_KIND,
            subsystem=rec.subsystem,
            authority_ref="",          # the ADMIN floor (settings.bind's own)
            # ``target_name`` rides ABOVE the op-kind's declared minimum
            # (the suggestion-edit slice): the final-review pending line
            # prefers it over the raw id (draft_render._short_label's
            # bind branch), so a renamed suggestion round-trips into the
            # staged card; the settings.bind legs read only their own
            # params and ignore it. Pre-slice staged rows lack the key —
            # the renderer's ``<id>`` fallback still answers.
            payload={"subsystem": rec.subsystem, "name": rec.binding_name,
                     "kind": rec.target_kind, "resource_id": rec.target_id,
                     "target_name": rec.target_name},
            label=(f"{_SUGGESTIONS_LABEL_PREFIX}{rec.subsystem}."
                   f"{_BIND_CHANNEL_OP_KIND}")))
        staged += 1
    return staged


async def clear_guild_drafts(guild_id: int) -> int:
    """The oracle ``setup_draft.clear`` (the ``/setup-reset`` clearing
    branch): discard every open guild draft; returns the op count that
    was pending before."""
    from sb.kernel.draft.store import DraftStore

    store = DraftStore()
    drafts = await _open_guild_drafts(guild_id)
    cleared = sum(len(d.operations) for d in drafts)
    for draft in drafts:
        await store.discard(draft.draft_id)
    return cleared


# --- shared handler plumbing -----------------------------------------------------------

async def _refresh_own_panel(req, params: dict) -> bool:
    """Refresh the clicked panel's card in place (the shipped
    ``edit_message`` re-render; best-effort — a missing live session
    degrades to the caller's text reply)."""
    try:
        from sb.kernel.panels.engine import refresh_session_view

        message = getattr(req.origin, "message", None)
        message_key = str(getattr(message, "id", "") or "")
        if not message_key:
            return False
        return await refresh_session_view(req, message_key=message_key,
                                          params=params)
    except Exception:  # noqa: BLE001 — the reply below still lands
        logger.debug("setup wizard: panel refresh failed", exc_info=True)
        return False


async def _open(req, panel_id: str, args: dict | None = None) -> None:
    import dataclasses as _dc
    from types import SimpleNamespace

    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    if args:
        merged = {**dict(req.args or {}), **args}
        try:
            req = _dc.replace(req, args=merged)
        except TypeError:   # duck-typed request (headless drives)
            req = SimpleNamespace(**{**vars(req), "args": merged})
    await open_panel(PanelRef(panel_id), req)


async def _write_setting(req, subsystem: str, name: str, value: object):
    """One audited write through the K7 ``settings.set_scalar`` op — the
    oracle ``_StepView._set`` (SettingsMutationPipeline.set_value) twin;
    booleans serialize to the legacy-KV "true"/"false" spellings."""
    from sb.kernel import settings as ksettings
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    serialized = ("true" if value else "false") if isinstance(value, bool) \
        else str(value)
    return await engine.run(
        WorkflowRef("settings.set_scalar"),
        ctx_from_request(req, {
            "key": ksettings.persisted_key(subsystem, name),
            "value": serialized,
            "subsystem": subsystem,
            "name": name,
        }))


# --- handlers --------------------------------------------------------------------------

def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.depth_pick_quick")):
        return

    # ---- the depth chooser's three buttons (depth_panel._select) ----

    def _depth_handler(depth: str):
        async def _pick(req) -> Reply | None:
            """Persist the choice (setup.set_depth — no session row is a
            silent no-op, the shipped UPDATE semantics), then land on the
            sections hub at that depth (the shipped ``after="hub"``
            default destination; the ``after="wizard"`` step-0 render is
            LIVE at the hub's ↩ Back to wizard — the chooser keeps the
            ONE hub landing because the ported panel lane carries no
            per-presentation ``after`` facet, ledgered: one click more
            than the oracle's workspace-anchor path)."""
            from sb.kernel.workflow import engine
            from sb.spec.refs import WorkflowRef

            try:
                result = await engine.run(WorkflowRef("setup.set_depth"),
                                          ctx_from_request(req, {"depth": depth}))
            except Exception:  # noqa: BLE001 — the shipped error copy answers
                logger.exception("setup wizard: set_depth failed (depth=%s)",
                                 depth)
                result = None
            if result is None or result.outcome != SUCCESS:
                # shipped copy, verbatim (depth_panel._select).
                return Reply(BLOCKED,
                             "Could not save your depth choice. See logs.")
            await _open(req, "setup.sections_hub")
            return None
        return _pick

    for _slug in ("quick", "standard", "advanced"):
        handler(f"setup.depth_pick_{_slug}")(_depth_handler(_slug))

    # ---- the sections hub (hub.SetupHubView) ----

    def _section_handler(slug: str):
        async def _open_section(req) -> Reply:
            """Gate exactly like the shipped hub button, then hold the
            honest named-successor terminal — the per-section flow is
            the section-flows slice's port."""
            if not await can_apply_setup(req):
                return Reply(BLOCKED, GATE_MSG_WIZARD)
            return Reply(BLOCKED,
                         f"🚧 The `{slug}` section's flow isn't armed in "
                         "this build yet — it lands with the "
                         "section-flows slice. `/setup-skip "
                         f"section:{slug}` marks it skipped meanwhile.")
        return _open_section

    from sb.domain.setup.sections import SECTIONS

    #: slugs whose flows are LIVE — their own modules register the
    #: ``setup.open_section_*`` route (final_review.py · the
    #: section-flows slice's preset_select.py + channels.py · the
    #: settings-write slice's logging_presets.py + moderation.py +
    #: cleanup.py · the roles-family slice's roles.py +
    #: role_templates.py).
    _LIVE_SECTIONS = frozenset({"final_review", "preset_select", "channels",
                                "logging_presets", "moderation", "cleanup",
                                "roles", "role_templates"})

    for _section in SECTIONS:
        if _section.slug in _LIVE_SECTIONS:
            continue
        handler(f"setup.open_section_{_section.slug}")(
            _section_handler(_section.slug))

    @handler("setup.change_depth")
    async def change_depth(req) -> Reply | None:
        """The hub's Change-depth button: re-enter the depth chooser
        (the shipped DepthPanelView re-open, gate first)."""
        if not await can_apply_setup(req):
            return Reply(BLOCKED, GATE_MSG_WIZARD)
        await _open(req, "setup.hub")
        return None

    # ``setup.back_to_wizard`` is LIVE — the section-flows slice's
    # linear wizard steps (sb/domain/setup/wizard_nav.py registers it).

    # ---- the essential Step-1 interior (essential_setup.ServerTypeStep) ----

    @handler("setup.essential_pick")
    async def essential_pick_handler(req) -> Reply | None:
        """The five-kind select: record the pick and re-render the card
        with its Starter-set field (the shipped ``_ServerTypeSelect.
        callback`` edit_message re-render)."""
        values = tuple(req.args.get("values", ()) or ())
        kind = str(values[0]) if values else ""
        preset = server_type(kind)
        if preset is None:
            # shipped defensive copy, verbatim (ServerTypeStep.apply —
            # the picker only offers known keys).
            return Reply(BLOCKED,
                         "That server type isn't available — please pick "
                         "another.")
        set_essential_pick(int(req.guild_id or 0),
                           int(getattr(req.actor, "user_id", 0) or 0), kind)
        refreshed = await _refresh_own_panel(
            req, {**dict(req.args or {}), "essential_kind": kind})
        if not refreshed:
            return Reply(SUCCESS,
                         f"Starter set selected: {preset.emoji} "
                         f"**{preset.label}** — press **Save & continue**.")
        return None

    @handler("setup.essential_save")
    async def essential_save(req) -> Reply | None:
        """✨ Save & continue: apply the picked starter set IMMEDIATELY
        through the audited settings lane (the oracle's direct-apply
        doctrine — "save each step instantly"), record the shipped
        applied-summary line, and advance to Step 2 (the essential-steps
        slice's spine — ``_StepView.complete``'s record + advance +
        show-current, the open_panel navigation lane)."""
        guild_id = int(req.guild_id or 0)
        user_id = int(getattr(req.actor, "user_id", 0) or 0)
        kind = essential_pick(guild_id, user_id)
        if kind is None:
            # shipped guard copy, verbatim (ServerTypeStep.apply).
            return Reply(BLOCKED,
                         "Pick the kind of server you run first — or press "
                         "Skip.")
        preset = server_type(kind)
        if preset is None:
            return Reply(BLOCKED,
                         "That server type isn't available — please pick "
                         "another.")
        try:
            for subsystem, name, value in preset.settings:
                result = await _write_setting(req, subsystem, name, value)
                if result.outcome != SUCCESS:
                    raise RuntimeError(
                        f"settings.set_scalar {subsystem}.{name} → "
                        f"{result.outcome}")
            if preset.xp_rate is not None:
                _label, xp_min, xp_max, cooldown = XP_RATES[preset.xp_rate]
                for name, value in (("xp_min", xp_min), ("xp_max", xp_max),
                                    ("xp_cooldown", cooldown)):
                    result = await _write_setting(req, "xp", name, value)
                    if result.outcome != SUCCESS:
                        raise RuntimeError(
                            f"settings.set_scalar xp.{name} → "
                            f"{result.outcome}")
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception("essential setup: server-type step apply failed")
            # shipped copy, verbatim (ServerTypeStep.apply).
            return Reply(BLOCKED,
                         "Something went wrong applying the starter set — "
                         "please try again.")
        # the shipped complete(): record the applied line (byte verbatim),
        # advance, land on the Step-2 card (essential_steps._show_current).
        from sb.domain.setup import essential_steps

        state = essential_steps.flow_state(guild_id, user_id)
        state.record_applied(
            f"{preset.emoji} {preset.label} starter set on · {preset.blurb}")
        state.index = 1
        await essential_steps._show_current(req, state)
        return None

    @handler("setup.essential_skip")
    async def essential_skip(req) -> Reply | None:
        """Skip — set things up myself: nothing changes; the shipped
        skip records the step and moves on to Step 2
        (``_StepView.skip`` — the essential-steps slice's spine)."""
        from sb.domain.setup import essential_steps

        state = essential_steps.flow_state(
            int(req.guild_id or 0),
            int(getattr(req.actor, "user_id", 0) or 0))
        state.record_skipped(essential_steps.STEP_TITLES[0])
        state.index = 1
        await essential_steps._show_current(req, state)
        return None

    # ---- the smart-suggestions review lanes (ai_review/main_panel) ----

    async def _refresh_review(req, state: ReviewState) -> None:
        await _refresh_own_panel(req, {
            "setup_plan_draft": state.draft,
            "review_status": state.last_status,
            "advisor_note": (req.args or {}).get("advisor_note"),
        })

    @handler("setup.review_accept_high")
    async def review_accept_high(req) -> Reply | None:
        """Accept all high-confidence → the AcceptedSet (main_panel.
        ``_accept_high``, verbatim status line)."""
        state = await review_state(int(req.guild_id or 0),
                                   int(getattr(req.actor, "user_id", 0) or 0))
        high = tuple(r for r in state.draft.recommendations
                     if r.confidence == "high")
        added = state.add_many(high)
        state.last_status = (
            f"Accepted {added} high-confidence recommendation(s); "
            f"total accepted: {state.count}.")
        if not await _refresh_own_panel(req, {
                "setup_plan_draft": state.draft,
                "review_status": state.last_status}):
            return Reply(SUCCESS, state.last_status)
        return None

    @handler("setup.review_one_by_one")
    async def review_one_by_one(req) -> Reply | None:
        """Review one-by-one → the per-suggestion walkthrough
        (main_panel ``_review_each``: the empty-draft guard verbatim,
        then the PerRecommendationView at index 0)."""
        state = await review_state(int(req.guild_id or 0),
                                   int(getattr(req.actor, "user_id", 0) or 0))
        if not state.draft.recommendations:
            # shipped copy, verbatim.
            return Reply(BLOCKED, "Nothing to review — the draft is empty.")
        state.index = 0
        await _open(req, "setup.review_item")
        return None

    @handler("setup.review_reject_ai")
    async def review_reject_ai(req) -> Reply | None:
        """Reject all AI suggestions (main_panel ``_reject_ai``): strip
        ``source == "openai"`` rows from draft + accepted set. The AI
        advisor lane is key-gated OFF in this build (the shipped
        build_advisor fallback), so the deterministic rows all survive —
        the shipped count line reports the truth either way."""
        state = await review_state(int(req.guild_id or 0),
                                   int(getattr(req.actor, "user_id", 0) or 0))
        recs = tuple(state.draft.recommendations)
        surviving = tuple(r for r in recs
                          if getattr(r, "source", "deterministic") != "openai")
        removed = len(recs) - len(surviving)
        if removed:
            state.draft = replace(
                state.draft, recommendations=surviving,
                source="deterministic")
        state.accepted = [r for r in state.accepted
                          if getattr(r, "source", "deterministic") != "openai"]
        state.last_status = (
            f"Rejected {removed} AI suggestion(s); accepted set "
            f"refreshed to {state.count}.")
        if not await _refresh_own_panel(req, {
                "setup_plan_draft": state.draft,
                "review_status": state.last_status}):
            return Reply(SUCCESS, state.last_status)
        return None

    @handler("setup.review_rerun")
    async def review_rerun(req) -> Reply | None:
        """Rerun deterministic-only (main_panel ``_rerun_deterministic``):
        re-run the deterministic advisor and replace the draft in place;
        AI-sourced accepted rows drop so the set stays consistent."""
        from sb.domain.setup import plan

        state = await review_state(int(req.guild_id or 0),
                                   int(getattr(req.actor, "user_id", 0) or 0))
        try:
            state.draft = await plan.suggest(int(req.guild_id or 0))
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception("setup wizard: deterministic rerun failed")
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "Deterministic rerun failed; the draft is "
                         "unchanged.")
        state.accepted = [r for r in state.accepted
                          if getattr(r, "source", "deterministic") != "openai"]
        state.last_status = (
            f"Deterministic advisor rerun: "
            f"{len(state.draft.recommendations)} recommendation(s); "
            f"accepted set: {state.count}.")
        if not await _refresh_own_panel(req, {
                "setup_plan_draft": state.draft,
                "review_status": state.last_status}):
            return Reply(SUCCESS, state.last_status)
        return None

    @handler("setup.review_stage")
    async def review_stage(req) -> Reply | None:
        """Stage & open Final review (main_panel ``_stage_final``): the
        shipped guards verbatim, then the accepted set lands in the K9
        draft (the sole apply path's staging leg — "nothing has changed
        yet") and the FINAL-REVIEW card opens (the shipped destination —
        the final-review slice's live lane)."""
        state = await review_state(int(req.guild_id or 0),
                                   int(getattr(req.actor, "user_id", 0) or 0))
        if not state.accepted:
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "Accept at least one suggestion first — use "
                         "**Accept all high-confidence** or **Review "
                         "one-by-one**.")
        if not await can_apply_setup(req):
            return Reply(BLOCKED, GATE_MSG_STAGE)
        try:
            staged = await stage_accepted(int(req.guild_id or 0),
                                          list(state.accepted))
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception("setup wizard: staging failed")
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "Could not stage the accepted suggestions — see "
                         "logs.")
        word = "operation" if staged == 1 else "operations"
        state.last_status = f"Staged {staged} {word} into the setup draft."
        await _refresh_own_panel(req, {
            "setup_plan_draft": state.draft,
            "review_status": state.last_status})
        # the shipped destination: the FinalReviewView opens over the
        # freshly staged draft (main_panel._stage_final's view swap —
        # the ported open_panel navigation lane).
        from sb.domain.setup.final_review import FINAL_REVIEW_PANEL_ID

        await _open(req, FINAL_REVIEW_PANEL_ID)
        return None

    # ---- the per-suggestion walkthrough (ai_review/per_recommendation) ----

    async def _return_to_overview(req, state: ReviewState) -> None:
        # shipped status line, verbatim (_return_to_overview).
        state.last_status = (
            f"Per-recommendation review finished; accepted set: "
            f"{state.count}.")
        await _open(req, "setup.suggestions_card", {
            "setup_plan_draft": state.draft,
            "review_status": state.last_status})

    async def _advance_or_return(req, state: ReviewState) -> None:
        state.index += 1
        if state.index >= len(state.draft.recommendations):
            await _return_to_overview(req, state)
            return
        if not await _refresh_own_panel(req, {}):
            await _open(req, "setup.review_item")

    @handler("setup.review_item_accept")
    async def review_item_accept(req) -> None:
        state = await review_state(int(req.guild_id or 0),
                                   int(getattr(req.actor, "user_id", 0) or 0))
        recs = state.draft.recommendations
        if 0 <= state.index < len(recs):
            state.add(recs[state.index])
            await _advance_or_return(req, state)
        else:
            await _return_to_overview(req, state)
        return None

    @handler("setup.review_item_deny")
    async def review_item_deny(req) -> None:
        state = await review_state(int(req.guild_id or 0),
                                   int(getattr(req.actor, "user_id", 0) or 0))
        recs = state.draft.recommendations
        if 0 <= state.index < len(recs):
            rec = recs[state.index]
            state.remove(rec.subsystem, rec.binding_name)
            await _advance_or_return(req, state)
        else:
            await _return_to_overview(req, state)
        return None

    @handler("setup.review_item_skip")
    async def review_item_skip(req) -> None:
        state = await review_state(int(req.guild_id or 0),
                                   int(getattr(req.actor, "user_id", 0) or 0))
        await _advance_or_return(req, state)
        return None

    @handler("setup.review_item_back")
    async def review_item_back(req) -> None:
        state = await review_state(int(req.guild_id or 0),
                                   int(getattr(req.actor, "user_id", 0) or 0))
        await _return_to_overview(req, state)
        return None

    # ---- the per-suggestion Edit lane (per_recommendation._edit +
    # _EditRecommendationModal — the suggestion-edit slice) ----

    def _bind_edit_refusal(rec) -> str:
        # shipped copy, verbatim (per_recommendation._edit's
        # can't-re-pick branch — the native picker sub-view is the
        # flagged follow-up, so every ``bind`` kind answers it).
        return (f"**Edit** can't re-pick a `{rec.target_kind}` here — "
                "**Deny** this suggestion and bind a different one if it "
                "isn't right.")

    @handler("setup.review_item_edit")
    async def review_item_edit(req) -> Reply | None:
        """Edit on a ``bind`` suggestion (the renderer's bind face):
        an existing resource can't be renamed — explain (oracle
        docstring: "A ``bind`` suggestion (an existing resource) can't
        be renamed — Edit explains that")."""
        state = await review_state(int(req.guild_id or 0),
                                   int(getattr(req.actor, "user_id", 0) or 0))
        recs = state.draft.recommendations
        if not (0 <= state.index < len(recs)):
            await _return_to_overview(req, state)
            return None
        rec = recs[state.index]
        if getattr(rec, "mode", "bind") == "create":
            # stale card (the create face renders the rename modal
            # button): re-render so the right Edit face shows.
            if not await _refresh_own_panel(req, {}):
                await _open(req, "setup.review_item")
            return None
        return Reply(BLOCKED, _bind_edit_refusal(rec))

    @handler("setup.review_item_edit_rename")
    async def review_item_edit_rename(req) -> Reply | None:
        """_EditRecommendationModal.on_submit → PerRecommendationView.
        apply_edit → _swap_and_accept, ported: rewrite the ``create``
        suggestion's target name in the shared draft, re-accept it
        under the (unchanged) binding key, advance the walkthrough.
        Pure in-memory state mutation — no DB write, no Discord
        resource creation (the edited op still applies only through
        the gated Final Review)."""
        state = await review_state(int(req.guild_id or 0),
                                   int(getattr(req.actor, "user_id", 0) or 0))
        recs = state.draft.recommendations
        if not (0 <= state.index < len(recs)):
            await _return_to_overview(req, state)
            return None
        rec = recs[state.index]
        if getattr(rec, "mode", "bind") != "create":
            # stale form (the walkthrough moved off the create
            # suggestion the form was opened on): the bind explanation
            # answers — nothing is changed.
            return Reply(BLOCKED, _bind_edit_refusal(rec))
        new_name = str(req.args.get("new_name") or "").strip()
        if not new_name:
            # shipped copy, verbatim (_EditRecommendationModal.on_submit).
            return Reply(BLOCKED,
                         "The name can't be empty — nothing was changed.")
        edited = replace(rec, target_name=new_name)
        swapped = list(recs)
        swapped[state.index] = edited
        state.draft = replace(state.draft,
                              recommendations=tuple(swapped))
        state.remove(rec.subsystem, rec.binding_name)
        state.add(edited)
        await _advance_or_return(req, state)
        return None


_register()
_register_op_kind()


def ensure_wizard_refs() -> None:
    _register()
    _register_op_kind()

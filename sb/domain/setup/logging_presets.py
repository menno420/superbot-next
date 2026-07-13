"""The LOGGING-PRESETS section flow (the settings-write slice), ported
from the oracle (menno420/superbot, read from the LOCAL oracle clone:
views/setup/sections/logging_presets.py):

* the LOGGING-BINDING CATALOGUE (``_LOGGING_BINDINGS``, data verbatim):
  the 8 logging-related channel bindings the wizard knows about, each
  carrying its ``general_logs`` / ``mod_logs`` intent and its Detailed
  channel name;
* the PRESET BUILDERS (``_preset_single_ops`` / ``_preset_balanced_ops``
  / ``_preset_detailed_ops``, semantics verbatim): every preset returns
  **only** ``create_channel`` ops — Single shares one
  ``#superbot-logs`` across every binding (name-based reuse), Balanced
  splits ``#bot-logs`` / ``#mod-logs`` by intent, Detailed mints one
  channel per binding;
* the PICKER (``build_logging_presets_embed`` + ``LoggingPresetsView``,
  bytes verbatim): the four-preset card with per-preset ✅ highlight,
  the Q-0109 privacy disclosure field, the shipped
  ``setup_logging_preset:*`` custom_ids; a preset click stages through
  ``replace_recommended_for_section`` (swapping presets cleanly
  removes the prior pick's rows, custom rows preserved) and answers
  the shipped staged confirmation; **Custom** delegates to the
  channels section's detail picker;
* APPLY RECOMMENDED (``_recommended_logging_ops``): the Balanced
  preset — the safest default, wired through the section-card spine's
  builder slot;
* ``infer_current_preset``: the reopened picker re-derives the
  highlight from the draft's recommended rows (1 distinct channel name
  → single; {bot-logs, mod-logs} → balanced; 3+ → detailed).

Kernel-idiom divergences, ledgered (the section_card.py doctrine):

* ``_supported_bindings`` filters the catalogue against the MANIFEST
  BindingSpec walk (channels.all_channel_bindings — this
  architecture's ``all_schemas()`` twin); the oracle's duck-typed
  runtime-schema check answered the same question;
* the ``create_channel`` op kind BINDS to the audited K7
  ``setup.ensure_channel`` compound op (the compound-ops slice — this
  module's previous fail-closed decide-and-flag, resolved): name-based
  reuse through the ChannelDirectory READ port (get-before-create is
  DOMAIN logic, D-0077 — the exact shared-channel semantics the preset
  builders rely on: the first ``#superbot-logs`` op creates, the rest
  reuse-and-bind) → create through the channel-state port → slot bind
  through ``settings.bind`` (bind failure NEVER undoes the channel —
  the oracle ``binding_failed`` outcome) → the K7 engine's ONE central
  audit row. The staged rows carry ``subsystem``/``name``/``kind``/
  ``resource_name`` (the binding's payload schema) and final-review's
  created-resources call-out renders from ``resource_name``;
* preset rows ride ``replace_recommended_for_section`` so the label
  carries ``[recommended:logging_presets] `` + the oracle's cosmetic
  ``[{preset}] {subsystem}.{binding} → #{channel}`` tail (the oracle
  section_slug/staging_kind columns have no K9 twin — the section_card
  label micro-grammar);
* the picker's Cancel answered as a disabled-view edit; here the
  shipped-copy-free close answers as a text reply (the ledgered
  text-reply seam);
* staged K9 rows carry no oracle metadata dict — the final_review.py
  ledger note's class.

NO GOLDEN drives any of these components (the panels.py module pin);
the oracle SOURCES pin the copy, and every golden-pinned OPEN render
stays byte-identical.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = [
    "GATE_MSG_LOGGING",
    "LOGGING_PICKER_PANEL_ID",
    "LoggingBinding",
    "build_logging_presets_embed",
    "ensure_logging_presets_refs",
    "infer_current_preset",
    "logging_picker_spec",
    "preset_ops",
    "recommended_logging_ops",
    "supported_bindings",
]

logger = logging.getLogger("sb.domain.setup")

SLUG = "logging_presets"

LOGGING_PICKER_PANEL_ID = "setup.logging_picker"

#: shipped gate refusal, verbatim (logging_presets._gate_apply).
GATE_MSG_LOGGING = ("Only the server owner or a delegated setup admin can "
                    "stage logging presets.  Ask the owner to grant you "
                    "`/setup-delegate`.")

#: the shipped card copy, verbatim (logging_presets.run's ``detected``).
_DETECTED_STATE = (
    "Logging presets stage create_channel ops only; Final Review "
    "confirms before any channel is touched.  Apply Recommended "
    "stages the **Balanced** preset (one general log channel + "
    "one mod log channel).  Customize opens the picker so you "
    "can choose Single / Balanced / Detailed / Custom.")


# --- the logging-binding catalogue (data verbatim) ---------------------------------------

@dataclass(frozen=True)
class LoggingBinding:
    """One logging-related channel binding the wizard knows about
    (logging_presets.LoggingBinding, verbatim shape)."""

    subsystem: str
    binding_name: str
    intent: str                 # "general_logs" | "mod_logs"
    detailed_channel_name: str  # used by the Detailed preset


_LOGGING_BINDINGS: tuple[LoggingBinding, ...] = (
    LoggingBinding(subsystem="moderation", binding_name="mod_channel",
                   intent="mod_logs", detailed_channel_name="mod-logs"),
    LoggingBinding(subsystem="logging", binding_name="cleanup_channel",
                   intent="general_logs",
                   detailed_channel_name="cleanup-logs"),
    LoggingBinding(subsystem="logging", binding_name="debug_channel",
                   intent="general_logs",
                   detailed_channel_name="debug-logs"),
    LoggingBinding(subsystem="logging", binding_name="info_channel",
                   intent="general_logs", detailed_channel_name="info-logs"),
    LoggingBinding(subsystem="logging", binding_name="warning_channel",
                   intent="general_logs",
                   detailed_channel_name="warning-logs"),
    LoggingBinding(subsystem="logging", binding_name="error_channel",
                   intent="general_logs", detailed_channel_name="error-logs"),
    LoggingBinding(subsystem="logging", binding_name="audit_channel",
                   intent="general_logs", detailed_channel_name="audit-logs"),
    LoggingBinding(subsystem="economy", binding_name="log_channel",
                   intent="general_logs",
                   detailed_channel_name="economy-logs"),
)


def supported_bindings() -> tuple[LoggingBinding, ...]:
    """logging_presets._supported_bindings over the manifest BindingSpec
    walk: catalogue entries whose (subsystem, binding) is declared as a
    CHANNEL binding; the oracle's runtime-schema duck-check answered
    the same question. Any walk failure falls back to the full
    catalogue (the oracle's own exception posture)."""
    from sb.domain.setup.channels import all_channel_bindings

    try:
        declared = {(sub, name)
                    for sub, name, _r, _h in all_channel_bindings()}
    except Exception:  # noqa: BLE001 — the oracle's schema-lookup fallback
        logger.exception(
            "logging_presets._supported_bindings: schema lookup failed")
        return _LOGGING_BINDINGS
    return tuple(entry for entry in _LOGGING_BINDINGS
                 if (entry.subsystem, entry.binding_name) in declared)


# --- the op-kind registration (the roles.py set_role_threshold precedent) -----------------

_CREATE_CHANNEL_OP_KIND = "create_channel"


def _register_create_channel_op_kind() -> None:
    """Bind the ``create_channel`` op kind onto the audited K7
    ``setup.ensure_channel`` compound op (the module docstring's named
    successor, landed by the compound-ops slice): name-based reuse or
    create through the D-0077 channel ports, then the slot bind through
    ``settings.bind`` — the oracle ResourceProvisioningPipeline route
    (setup_operations.py:1127 → _apply_resource_create:1310)."""
    from sb.kernel.draft.registry import OP_KINDS, OpKindBinding
    from sb.spec.events import FieldSpec
    from sb.spec.refs import WorkflowRef

    binding = OpKindBinding(
        op_kind=_CREATE_CHANNEL_OP_KIND,
        workflow_ref=WorkflowRef("setup.ensure_channel"),
        payload_schema=(FieldSpec("subsystem", "str"),
                        FieldSpec("name", "str"),
                        FieldSpec("kind", "str"),
                        FieldSpec("resource_name", "str")),
        is_resource_create=True)
    try:
        OP_KINDS.register(binding)
    except ValueError as exc:
        if "bound twice" not in str(exc):
            raise


# --- preset ops builders (semantics verbatim) ---------------------------------------------

def _build_create_op(entry: LoggingBinding, *, resource_name: str,
                     preset_key: str):
    """One ``create_channel`` op covering ``entry`` — the oracle
    _build_create_op shape over the K9 StagedSectionOp; the label tail
    is the shipped per-op label (LoggingPresetsView's ``labels``)."""
    from sb.domain.setup.section_card import StagedSectionOp

    _register_create_channel_op_kind()

    return StagedSectionOp(
        op_kind="create_channel", subsystem=entry.subsystem,
        payload={"subsystem": entry.subsystem, "name": entry.binding_name,
                 "kind": "channel", "resource_name": resource_name,
                 "resource_mode": "create"},
        label_body=(f"[{preset_key}] {entry.subsystem}."
                    f"{entry.binding_name} → #{resource_name}"))


def preset_ops(preset_key: str,
               bindings: tuple[LoggingBinding, ...]) -> list:
    """The three preset builders folded on the shipped semantics:
    single — N ops all pointing at ``superbot-logs`` (the first
    creates, the rest reuse by name); balanced — the two-channel
    intent split; detailed — one channel per binding."""
    if preset_key == "single":
        return [_build_create_op(b, resource_name="superbot-logs",
                                 preset_key=preset_key) for b in bindings]
    if preset_key == "balanced":
        return [_build_create_op(
            b,
            resource_name=("mod-logs" if b.intent == "mod_logs"
                           else "bot-logs"),
            preset_key=preset_key) for b in bindings]
    if preset_key == "detailed":
        return [_build_create_op(b, resource_name=b.detailed_channel_name,
                                 preset_key=preset_key) for b in bindings]
    return []


async def recommended_logging_ops(guild_id: int) -> list:
    """The wizard/hub Apply-Recommended builder — the Balanced preset
    (logging_presets._recommended_logging_ops: "the safest default —
    two purpose-built channels covering every supported binding")."""
    del guild_id
    bindings = supported_bindings()
    if not bindings:
        return []
    return preset_ops("balanced", bindings)


# --- current-preset inference (infer_current_preset, ported) -------------------------------

def infer_current_preset(ops) -> str | None:
    """single / balanced / detailed off the recommended rows this
    section owns (the oracle read section_slug + staging_kind columns;
    the label micro-grammar carries both here): 1 unique channel name
    → single; {bot-logs, mod-logs} → balanced; 3+ → detailed."""
    from sb.domain.setup.section_card import row_section

    names: set[str] = set()
    own = False
    for op in ops:
        slug, rec = row_section(str(getattr(op, "label", "") or ""))
        if slug != SLUG or not rec:
            continue
        own = True
        if str(getattr(op, "op_kind", "")) != "create_channel":
            continue
        payload = dict(getattr(op, "payload", {}) or {})
        name = str(payload.get("resource_name") or "")
        if name:
            names.add(name)
    if not own:
        return None
    if len(names) == 1:
        return "single"
    if names == {"bot-logs", "mod-logs"}:
        return "balanced"
    if len(names) >= 3:
        # Detailed uses one channel per binding, so unique-name count
        # tracks binding count.  3+ distinct names is detailed in
        # every realistic catalogue size.
        return "detailed"
    return None


# --- the picker embed (build_logging_presets_embed, bytes verbatim) ------------------------

def build_logging_presets_embed(supported: tuple[LoggingBinding, ...], *,
                                current_preset: str | None = None):
    from sb.kernel.panels.render import RenderedEmbed

    binding_count = len(supported)
    counts_by_intent = {
        intent: sum(1 for b in supported if b.intent == intent)
        for intent in ("general_logs", "mod_logs")
    }
    fields: tuple = (
        (("✅ Single" if current_preset == "single" else "Single"),
         (f"One channel `#superbot-logs`.  Binds **{binding_count}** "
          "logging slot(s).  Lowest overhead; everything in one inbox."),
         False),
        (("✅ Balanced" if current_preset == "balanced" else "Balanced"),
         (f"`#bot-logs` for general logs "
          f"(**{counts_by_intent['general_logs']}** slot(s)) and "
          f"`#mod-logs` for moderation "
          f"(**{counts_by_intent['mod_logs']}** slot(s))."),
         False),
        (("✅ Detailed" if current_preset == "detailed" else "Detailed"),
         (f"One channel per slot — **{binding_count}** purpose-built "
          "channels (`#audit-logs`, `#mod-logs`, `#debug-logs`, …)."),
         False),
        ("Custom",
         ("Skip the preset and bind each channel yourself via the "
          "**Customize** button below.  No operations staged."),
         False),
        # Q-0109 privacy disclosure — carried verbatim (the owner
        # requirement that the wizard discloses it).
        ("🔒 Privacy — server event logging",
         ("Server event logging (message edits/deletions, joins/leaves, "
          "role changes) is **off by default**.  If you enable message "
          "logging, **staff can see the content of messages members "
          "edited or deleted**.  Turn categories on per-server in "
          "`!settings → Logging`."),
         False),
    )
    return RenderedEmbed(
        title="📜 Logging presets",
        description=(
            "Pick how SuperBot routes its log channels.  Every preset "
            "stages **`create_channel`** operations only — Final "
            "Review confirms before any channel is touched.  Switching "
            "presets cleanly removes the prior pick's staged rows."),
        fields=fields,
        footer=("Nothing applies until Final Review.  Switching presets "
                "replaces the prior pick — your staged custom bindings "
                "stay intact."),
        style_token="blurple")


# --- the picker panel ------------------------------------------------------------------------

def logging_picker_spec():
    """LoggingPresetsView folded onto one panel: the three preset
    buttons + Custom on row 0 (labels/styles/emoji verbatim, the
    shipped ``setup_logging_preset:*`` custom_ids compat-pinned),
    Cancel on row 1, and the wizard-origin ↩ Back to step button."""
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        NavigationSpec, PageSpec, PanelActionSpec, PanelSpec,
    )
    from sb.spec.refs import HandlerRef

    return PanelSpec(
        panel_id=LOGGING_PICKER_PANEL_ID,
        subsystem="setup",
        title="📜 Logging presets",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="logging_single", label="Single channel",
                emoji="📥", style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.logging_preset_single"),
                custom_id_override="setup_logging_preset:single"),
            PanelActionSpec(
                action_id="logging_balanced", label="Balanced",
                emoji="📚", style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.logging_preset_balanced"),
                custom_id_override="setup_logging_preset:balanced"),
            PanelActionSpec(
                action_id="logging_detailed", label="Detailed",
                emoji="🗂", style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.logging_preset_detailed"),
                custom_id_override="setup_logging_preset:detailed"),
            PanelActionSpec(
                action_id="logging_custom", label="Custom",
                emoji="🛠", style=ActionStyle.PRIMARY,
                handler=HandlerRef("setup.logging_preset_custom"),
                custom_id_override="setup_logging_preset:custom"),
            PanelActionSpec(
                action_id="logging_cancel", label="Cancel",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.logging_preset_cancel"),
                custom_id_override="setup_logging_preset:cancel"),
            PanelActionSpec(
                action_id="logging_back_step", label="↩ Back to step",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.wizard_back_to_step")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("logging_single", "logging_balanced", "logging_detailed",
             "logging_custom"),
            ("logging_cancel",),
            ("logging_back_step",))),)),
        renderer_override=HandlerRef("setup.logging_picker_render"),
        justification=(
            "the shipped logging-presets picker is draft-parameterized "
            "end to end (the per-preset ✅ field highlight and the "
            "success-style repaint of the current pick — "
            "logging_presets.build_logging_presets_embed + "
            "LoggingPresetsView._populate_buttons), its binding counts "
            "come from the runtime-filtered catalogue, and its ↩ Back "
            "to step button rides only the wizard-native path "
            "(wizard_nav's injection ledger note) — outside the static "
            "grammar vocabulary; the override composes the embed and "
            "patches the components (no golden pins it — the oracle "
            "source does)."),
        session_lifecycle=True,
    )


async def _render_logging_picker(spec, ctx):
    import dataclasses

    from sb.domain.setup import section_card, wizard_nav
    from sb.kernel.panels.render import render_panel

    guild_id = int(ctx.guild_id or 0)
    user_id = int(getattr(ctx.actor, "user_id", 0) or 0)
    try:
        ops = [op for _d, op in await section_card.guild_ops(guild_id)]
    except Exception:  # noqa: BLE001 — the shipped list_rows soft-fail
        logger.exception("logging_presets.customize: list_rows failed")
        ops = []
    current = infer_current_preset(ops)
    embed = build_logging_presets_embed(supported_bindings(),
                                        current_preset=current)

    base = await render_panel(spec, ctx)
    from_wizard = wizard_nav.detail_from_wizard(guild_id, user_id)
    highlighted = f"setup_logging_preset:{current}" if current else ""
    components = []
    for c in base.components:
        if c.custom_id == highlighted:
            # the shipped highlight repaint (success when picked).
            c = dataclasses.replace(c, style="success")
        elif (c.custom_id.endswith(".logging_back_step")
                and not from_wizard):
            continue        # the shipped wizard-native-only injection
        components.append(c)
    return dataclasses.replace(base, embed=embed,
                               components=tuple(components))


# --- handlers ---------------------------------------------------------------------------------

def _preset_click(preset_key: str):
    async def _pick(req) -> Reply | None:
        """LoggingPresetsView._make_preset_callback, ported: gate, build
        the preset's create_channel ops over the supported catalogue,
        replace the section's recommended rows, unmark the skip, repaint
        the picker, answer the shipped confirmation."""
        from sb.domain.setup import section_card, wizard
        from sb.domain.setup.wizard import _refresh_own_panel

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, GATE_MSG_LOGGING)
        guild_id = int(req.guild_id or 0)
        if not guild_id:
            # shipped copy, verbatim.
            return Reply(BLOCKED, "This can only be used in a server.")
        bindings = supported_bindings()
        if not bindings:
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "No logging bindings are available in this "
                         "runtime.")
        ops = preset_ops(preset_key, bindings)
        try:
            result = await section_card.replace_recommended_for_section(
                guild_id, SLUG, ops)
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception(
                "logging_presets: replace_recommended failed (preset=%s)",
                preset_key)
            # shipped copy, verbatim.
            return Reply(BLOCKED, "Could not stage the preset — see logs.")
        if not await section_card.mark_section_skipped(req, SLUG,
                                                       skipped=False):
            logger.exception("logging_presets: unmark skip failed")
        await section_card.mark_step_in_progress(req, SLUG)
        # repaint with the new highlight (the shipped edit_message).
        await _refresh_own_panel(req, {})
        staged = result.inserted
        noun = "operation" if staged == 1 else "operations"
        extra = ""
        if result.conflicts:
            cn = len(result.conflicts)
            conflict_word = "row" if cn == 1 else "rows"
            extra = (f"\n\n⚠️ Preserved **{cn} custom / preset "
                     f"{conflict_word}** at conflicting slot(s); no "
                     "overwrite.")
        # shipped confirmation, verbatim.
        return Reply(SUCCESS,
                     f"✅ Staged **{staged} {noun}** for the "
                     f"**{preset_key}** preset.  Open Final Review to "
                     f"apply.{extra}")
    return _pick


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.logging_preset_single")):
        return

    @handler("setup.open_section_logging_presets")
    async def open_section_logging_presets(req) -> Reply | None:
        """The hub's Logging-presets section button — gate exactly like
        the shipped hub button, land on the section card
        (logging_presets.run → section_card.show), record the step
        marker."""
        from sb.domain.setup import section_card, wizard
        from sb.domain.setup.wizard import _open

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, wizard.GATE_MSG_WIZARD)
        await _open(req, section_card.card_panel_id(SLUG))
        await section_card.mark_step_in_progress(req, SLUG)
        return None

    for _key in ("single", "balanced", "detailed"):
        handler(f"setup.logging_preset_{_key}")(_preset_click(_key))

    @handler("setup.logging_preset_custom")
    async def logging_preset_custom(req) -> Reply | None:
        """Custom delegates to the channels section's detail picker so
        operators who want fine-grained control don't have to leave the
        wizard (logging_presets._on_custom — no gate here: the channels
        detail's mutating pick already enforces it)."""
        from sb.domain.setup.channels import CHANNELS_DETAIL_PANEL_ID
        from sb.domain.setup.wizard import _open

        try:
            await _open(req, CHANNELS_DETAIL_PANEL_ID)
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception(
                "logging_presets._on_custom: customize_run failed")
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "Could not open the channel picker — see logs.")
        return None

    @handler("setup.logging_preset_cancel")
    async def logging_preset_cancel(req) -> Reply:
        # the oracle disabled the view in place (no content) — the
        # ledgered text-reply seam answers the close.
        return Reply(SUCCESS, "Preset picker closed — draft unchanged.")


# --- registration ------------------------------------------------------------------------------

def _register_panels() -> None:
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    if not is_registered(HandlerRef("setup.logging_picker_render")):
        handler("setup.logging_picker_render")(_render_logging_picker)
    if not is_registered(PanelRef(LOGGING_PICKER_PANEL_ID)):
        panel(LOGGING_PICKER_PANEL_ID)(logging_picker_spec)


def _register_section() -> None:
    from sb.domain.setup import section_card

    section_card.register_recommended_builder(SLUG, recommended_logging_ops)
    section_card.register_customize_panel(SLUG, LOGGING_PICKER_PANEL_ID)
    section_card.register_section_card(SLUG, detected_state=_DETECTED_STATE)


_register()
_register_panels()
_register_section()
_register_create_channel_op_kind()


def ensure_logging_presets_refs() -> None:
    _register()
    _register_panels()
    _register_section()
    _register_create_channel_op_kind()

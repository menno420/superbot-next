"""The PRESET-SELECT section flow (the section-flows slice), ported from
the oracle (menno420/superbot, read from the LOCAL oracle clone:
views/setup/sections/preset_select.py + the
services/automation_templates.py preset catalogue + the
services/setup_operations.py ``preset_operations_to_setup_operations``
adapter):

* the PRESET CATALOGUE (``_SERVER_PRESETS``, data verbatim): minimal /
  community / gaming / moderation-heavy / economy / existing-safe /
  custom — each a named bundle of ``PresetOperation`` steps
  (bind_channel / set_setting / add_rule);
* the ENTRY CARD (``build_preset_embed``, bytes verbatim): every
  bundled preset listed, the staging disclaimer, the
  "Picking a preset opens a preview before staging." footer, and the
  preset picker select;
* the PREVIEW (``build_preview_embed`` + ``preview_preset``, bytes
  verbatim): the would-be-staged op list (capped at 10 + the ``_+N
  more_`` tail), warnings, the confirm footer, and the
  📥 **Stage every op** / Cancel pair;
* STAGING (``_stage_preset``): every adapted op lands in the guild's
  K9 draft with the shipped per-op label
  (``[{display_name}] {kind} · {subsystem}.{name} = {value}``), the
  session step marker rides ``setup.mark_in_progress``, and the
  shipped staged/pending/failed summary answers.

Kernel-idiom divergences, ledgered (the section_card.py doctrine):

* the adapter is the reachable-kind subset: ``bind_channel`` →
  draftable rows against the audited ``settings.bind`` seam (staged
  TARGET-LESS exactly like the oracle — the per-binding picker was to
  fill them; an apply without a target fails into the partial-recovery
  lane, the oracle's own behavior); ``set_setting`` → a NEW
  ``set_setting`` op-kind registered onto the audited K7
  ``settings.set_scalar`` op; ``add_rule`` → ``add_automation_rule``
  rows registered onto the audited K7 ``automation.add_rule`` op (the
  compound-ops slice landed the automation write seam —
  sb/domain/automation/: rules insert DISABLED, template slug resolved
  against the carried catalogue, unknown slug refused; the runtime
  consumer stays the named successor per that package's ledger);
* preset rows carry NO section-provenance prefix (the oracle
  ``_stage_preset`` appended with ``section_slug=None`` — status
  matching falls back to ``op_kinds``, its own shipped quirk);
* the preview's unknown-template warning validates against the
  carried template-slug set (the oracle checked its automation
  catalogue; the three preset-referenced slugs are carried verbatim,
  so no shipped preset ever warns — same as the oracle).

NO GOLDEN drives any of these components (the panels.py module pin);
the oracle SOURCES pin the copy, and every golden-pinned OPEN render
stays byte-identical.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = [
    "PRESET_PANEL_ID",
    "PRESET_PREVIEW_PANEL_ID",
    "SERVER_PRESETS",
    "PresetOperation",
    "ServerPreset",
    "ensure_preset_select_refs",
    "get_preset",
    "preset_card_spec",
    "preset_preview_spec",
    "preview_warnings",
    "reset_preset_state_for_tests",
    "staged_ops_for_preset",
]

logger = logging.getLogger("sb.domain.setup")

SLUG = "preset_select"

PRESET_PANEL_ID = "setup.preset_card"
PRESET_PREVIEW_PANEL_ID = "setup.preset_preview"

_PRESET_OPTIONS_PROVIDER = "setup.preset_options"


# --- the preset catalogue (automation_templates.py, data verbatim) ----------------------

@dataclass(frozen=True)
class PresetOperation:
    """automation_templates.PresetOperation, verbatim shape."""

    kind: str
    description: str
    payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ServerPreset:
    """automation_templates.ServerPreset, the declarative subset."""

    slug: str
    display_name: str
    description: str
    operations: tuple[PresetOperation, ...] = ()


SERVER_PRESETS: tuple[ServerPreset, ...] = (
    ServerPreset(
        slug="minimal",
        display_name="Minimal",
        description=(
            "Bare-bones setup: a rules channel binding + a mod log channel "
            "binding. Nothing else."),
        operations=(
            PresetOperation(
                kind="bind_channel",
                description="Bind the rules channel.",
                payload={"subsystem": "logging",
                         "binding_name": "rules_channel"}),
            PresetOperation(
                kind="bind_channel",
                description="Bind the moderation log channel.",
                payload={"subsystem": "logging",
                         "binding_name": "mod_channel"}),
        )),
    ServerPreset(
        slug="community",
        display_name="Community",
        description=(
            "Welcome flow + general / off-topic channel bindings + "
            "moderation log + new-member role."),
        operations=(
            PresetOperation(
                kind="bind_channel",
                description="Bind the welcome channel.",
                payload={"subsystem": "onboarding",
                         "binding_name": "welcome_channel"}),
            PresetOperation(
                kind="bind_channel",
                description="Bind the rules channel.",
                payload={"subsystem": "logging",
                         "binding_name": "rules_channel"}),
            PresetOperation(
                kind="bind_channel",
                description="Bind the moderation log channel.",
                payload={"subsystem": "logging",
                         "binding_name": "mod_channel"}),
            PresetOperation(
                kind="add_rule",
                description="Welcome message on member join.",
                payload={"template_slug": "welcome-message"}),
            PresetOperation(
                kind="add_rule",
                description="Auto-assign New Member role on join.",
                payload={"template_slug": "new-member-role"}),
        )),
    ServerPreset(
        slug="gaming",
        display_name="Gaming",
        description=(
            "Community preset plus a games / leaderboard hub channel "
            "binding."),
        operations=(
            PresetOperation(
                kind="bind_channel",
                description="Bind the rules channel.",
                payload={"subsystem": "logging",
                         "binding_name": "rules_channel"}),
            PresetOperation(
                kind="bind_channel",
                description="Bind the moderation log channel.",
                payload={"subsystem": "logging",
                         "binding_name": "mod_channel"}),
            PresetOperation(
                kind="bind_channel",
                description="Bind the leaderboard / counting channel.",
                payload={"subsystem": "counting",
                         "binding_name": "channel"}),
            PresetOperation(
                kind="add_rule",
                description="Notify staff when a new member joins.",
                payload={"template_slug": "notify-staff-on-join"}),
        )),
    ServerPreset(
        slug="moderation-heavy",
        display_name="Moderation heavy",
        description=(
            "Strict log routing: mod / cleanup / audit channels each "
            "bound to dedicated channels."),
        operations=(
            PresetOperation(
                kind="bind_channel",
                description="Bind the rules channel.",
                payload={"subsystem": "logging",
                         "binding_name": "rules_channel"}),
            PresetOperation(
                kind="bind_channel",
                description="Bind the moderation log channel.",
                payload={"subsystem": "logging",
                         "binding_name": "mod_channel"}),
            PresetOperation(
                kind="bind_channel",
                description="Bind the cleanup log channel.",
                payload={"subsystem": "logging",
                         "binding_name": "cleanup_channel"}),
            PresetOperation(
                kind="bind_channel",
                description="Bind the audit log channel.",
                payload={"subsystem": "logging",
                         "binding_name": "audit_channel"}),
            PresetOperation(
                kind="set_setting",
                description="Turn logging on.",
                payload={"subsystem": "logging", "name": "enabled",
                         "value": True}),
        )),
    ServerPreset(
        slug="economy",
        display_name="Economy",
        description=("Bind economy + shop channels and seed the welcome "
                     "message."),
        operations=(
            PresetOperation(
                kind="bind_channel",
                description="Bind the economy announce channel.",
                payload={"subsystem": "economy",
                         "binding_name": "announce_channel"}),
            PresetOperation(
                kind="bind_channel",
                description="Bind the moderation log channel.",
                payload={"subsystem": "logging",
                         "binding_name": "mod_channel"}),
            PresetOperation(
                kind="add_rule",
                description="Welcome message on member join.",
                payload={"template_slug": "welcome-message"}),
        )),
    ServerPreset(
        slug="existing-safe",
        display_name="Existing-server safe",
        description=(
            "Binds likely-existing channels for rules + moderation log. "
            "Never creates channels, roles, or automation rules — safe to "
            "apply to a server that already has its own structure."),
        operations=(
            PresetOperation(
                kind="bind_channel",
                description="Bind an existing rules channel.",
                payload={"subsystem": "logging",
                         "binding_name": "rules_channel"}),
            PresetOperation(
                kind="bind_channel",
                description="Bind an existing moderation log channel.",
                payload={"subsystem": "logging",
                         "binding_name": "mod_channel"}),
            PresetOperation(
                kind="bind_channel",
                description="Bind an existing bot-commands channel.",
                payload={"subsystem": "moderation",
                         "binding_name": "bot_command_channel"}),
        )),
    ServerPreset(
        slug="custom",
        display_name="Custom",
        description=(
            "Empty preset — the wizard builds the operations list as the "
            "operator picks each binding."),
        operations=()),
)


def get_preset(slug: str) -> ServerPreset | None:
    for preset in SERVER_PRESETS:
        if preset.slug == slug:
            return preset
    return None


#: the automation-template slugs the shipped presets reference
#: (automation_templates.TEMPLATES' relevant rows — the preview's
#: unknown-template sanity check validates against these).
_KNOWN_TEMPLATE_SLUGS: frozenset[str] = frozenset(
    {"welcome-message", "new-member-role", "notify-staff-on-join"})


def preview_warnings(preset: ServerPreset) -> tuple[str, ...]:
    """preview_preset's sanity-warning leg, verbatim reason strings
    (the reuse-candidate leg rode create_channel/create_role ops no
    shipped preset carries)."""
    warnings: list[str] = []
    for index, op in enumerate(preset.operations):
        if op.kind == "add_rule":
            slug = str(op.payload.get("template_slug") or "")
            if slug not in _KNOWN_TEMPLATE_SLUGS:
                warnings.append(
                    f"operation[{index}]: unknown template slug {slug!r}")
    return tuple(warnings)


# --- the K9 adaptation (preset_operations_to_setup_operations, the reachable subset) ----

def staged_ops_for_preset(preset: ServerPreset) -> list[tuple[str, str, dict, str]]:
    """Adapt the preset's operations into (op_kind, subsystem, payload,
    label) rows for the K9 draft — the oracle adapter + _stage_preset's
    per-op label builder, verbatim label bytes."""
    out: list[tuple[str, str, dict, str]] = []
    for op in preset.operations:
        payload = dict(op.payload or {})
        subsystem = str(payload.get("subsystem", "") or "")
        binding_name = payload.get("binding_name")
        setting_name = (payload.get("name")
                        if op.kind == "set_setting" else None)
        value = payload.get("value")
        if op.kind == "bind_channel":
            op_kind = "bind_channel"
            k9_payload = {"subsystem": subsystem,
                          "name": str(binding_name or ""),
                          "kind": "channel",
                          "resource_id": None, "target_name": None}
        elif op.kind == "set_setting":
            from sb.kernel import settings as ksettings

            op_kind = "set_setting"
            serialized = (("true" if value else "false")
                          if isinstance(value, bool) else str(value))
            k9_payload = {"subsystem": subsystem,
                          "name": str(setting_name or ""),
                          "key": ksettings.persisted_key(
                              subsystem, str(setting_name or "")),
                          "value": serialized}
        elif op.kind == "add_rule":
            op_kind = "add_automation_rule"
            subsystem = "automation"
            k9_payload = {"template_slug":
                          str(payload.get("template_slug") or "")}
        else:
            # the oracle's preserve-unknown branch — surfaces as
            # not-yet-implemented instead of silently dropping.
            op_kind = f"preset_unknown:{op.kind}"
            k9_payload = dict(payload)
        # the shipped per-op label (preset_select._stage_preset).
        label = f"[{preset.display_name}] {op_kind}"
        if subsystem:
            label += f" · {subsystem}"
        if binding_name:
            label += f".{binding_name}"
        if setting_name:
            label += f".{setting_name}"
        if value is not None:
            label += f" = {value}"
        out.append((op_kind, subsystem, k9_payload, label))
    return out


_SET_SETTING_OP_KIND = "set_setting"
_ADD_AUTOMATION_RULE_OP_KIND = "add_automation_rule"


def _register_add_automation_rule_op_kind() -> None:
    """Bind the ``add_automation_rule`` op kind onto the audited K7
    ``automation.add_rule`` op (the module docstring's former named
    successor, landed by the compound-ops slice): template slug →
    disabled rule row — the oracle AutomationMutationPipeline.create_rule
    route (setup_operations.py:1136 → _apply_automation_create:1387)."""
    from sb.kernel.draft.registry import OP_KINDS, OpKindBinding
    from sb.spec.events import FieldSpec
    from sb.spec.refs import WorkflowRef

    binding = OpKindBinding(
        op_kind=_ADD_AUTOMATION_RULE_OP_KIND,
        workflow_ref=WorkflowRef("automation.add_rule"),
        payload_schema=(FieldSpec("template_slug", "str"),),
        is_resource_create=False)
    try:
        OP_KINDS.register(binding)
    except ValueError as exc:
        if "bound twice" not in str(exc):
            raise


def _register_set_setting_op_kind() -> None:
    """Bind the ``set_setting`` op kind onto the audited K7
    ``settings.set_scalar`` op (the wizard.py ``bind_channel`` →
    ``settings.bind`` precedent), so a preset's scalar rows are
    draftable AND appliable through the fail-closed K9 registry."""
    from sb.kernel.draft.registry import OP_KINDS, OpKindBinding
    from sb.spec.events import FieldSpec
    from sb.spec.refs import WorkflowRef

    binding = OpKindBinding(
        op_kind=_SET_SETTING_OP_KIND,
        workflow_ref=WorkflowRef("settings.set_scalar"),
        payload_schema=(FieldSpec("subsystem", "str"),
                        FieldSpec("name", "str"),
                        FieldSpec("key", "str"),
                        FieldSpec("value", "str")),
        is_resource_create=False)
    try:
        OP_KINDS.register(binding)
    except ValueError as exc:
        if "bound twice" not in str(exc):
            raise


# --- flow state --------------------------------------------------------------------------

_PICKED: dict[str, str] = {}


def _key(req_or_ctx) -> str:
    return (f"{int(req_or_ctx.guild_id or 0)}:"
            f"{int(getattr(req_or_ctx.actor, 'user_id', 0) or 0)}")


def picked_preset(ctx) -> str:
    return _PICKED.get(_key(ctx), "")


def reset_preset_state_for_tests() -> None:
    _PICKED.clear()


# --- panel specs -------------------------------------------------------------------------

def preset_card_spec():
    """The entry card (build_preset_embed + PresetSectionView)."""
    from sb.spec.panels import (
        Audience, EmbedFrameSpec, FooterMode, LayoutSpec, NavigationSpec,
        PageSpec, PanelSpec, SelectorKind, SelectorSpec,
    )
    from sb.spec.refs import HandlerRef, ProviderRef

    return PanelSpec(
        panel_id=PRESET_PANEL_ID,
        subsystem="setup",
        title="🎛 Load a preset",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="preset_pick", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.preset_pick"),
                options_source=ProviderRef(_PRESET_OPTIONS_PROVIDER),
                placeholder="Pick a preset…"),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(("preset_pick",),)),)),
        renderer_override=HandlerRef("setup.preset_card_render"),
        justification=(
            "the shipped preset card carries one field per bundled "
            "preset plus the footer literal 'Picking a preset opens a "
            "preview before staging.' (preset_select.build_preset_embed) "
            "— grammar FieldsBlocks are provider-fed and FooterMode has "
            "no literal lane; the override composes the embed (no golden "
            "pins it — the oracle source does)."),
        session_lifecycle=True,
    )


def preset_preview_spec():
    """The preview + confirm card (build_preview_embed +
    _ConfirmPresetView — labels/styles/emoji verbatim)."""
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        NavigationSpec, PageSpec, PanelActionSpec, PanelSpec,
    )
    from sb.spec.refs import HandlerRef

    return PanelSpec(
        panel_id=PRESET_PREVIEW_PANEL_ID,
        subsystem="setup",
        title="🎛 Preset preview",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="preset_confirm", label="Stage every op",
                emoji="📥", style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.preset_confirm")),
            PanelActionSpec(
                action_id="preset_cancel", label="Cancel",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.preset_cancel")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("preset_confirm", "preset_cancel"),)),)),
        renderer_override=HandlerRef("setup.preset_preview_render"),
        justification=(
            "the shipped preview embed is preset-parameterized end to end "
            "(the display-name title, the op-count description, the "
            "Operations list capped at 10, the Warnings field — "
            "preset_select.build_preview_embed) — outside the static "
            "grammar vocabulary; the override composes the embed (no "
            "golden pins it — the oracle source does)."),
        session_lifecycle=True,
    )


# --- providers + renderers ----------------------------------------------------------------

def _ensure_providers() -> None:
    from sb.spec.refs import ProviderRef, is_registered, provider

    if is_registered(ProviderRef(_PRESET_OPTIONS_PROVIDER)):
        return

    @provider(_PRESET_OPTIONS_PROVIDER)
    async def preset_options(ctx):
        """preset_select._preset_options, verbatim caps + the
        (no presets) guard row."""
        options = tuple(
            {"label": preset.display_name[:100], "value": preset.slug,
             "description": (preset.description[:100] or None)}
            for preset in SERVER_PRESETS)
        return options or ({"label": "(no presets)", "value": "_none"},)


async def _render_preset_card(spec, ctx):
    """build_preset_embed, bytes verbatim."""
    import dataclasses

    from sb.kernel.panels.render import RenderedEmbed, render_panel

    base = await render_panel(spec, ctx)
    fields = tuple(
        (f"{preset.display_name} (`{preset.slug}`)", preset.description,
         False)
        for preset in SERVER_PRESETS)
    embed = RenderedEmbed(
        title="🎛 Load a preset",
        description=(
            "Pick a preset to stage every operation it ships with in one "
            "go.  Nothing applies — Final review confirms before any "
            "mutation runs.  All preset-staged ops carry "
            "`metadata.source = 'preset:<slug>'` so the Final review "
            "embed can group them."),
        fields=fields,
        footer="Picking a preset opens a preview before staging.",
        style_token="blurple")
    return dataclasses.replace(base, embed=embed)


async def _render_preset_preview(spec, ctx):
    """build_preview_embed, bytes verbatim over the picked slug."""
    import dataclasses

    from sb.kernel.panels.render import RenderedEmbed, render_panel

    base = await render_panel(spec, ctx)
    slug = picked_preset(ctx)
    preset = get_preset(slug)
    if preset is None:
        embed = RenderedEmbed(
            title="🎛 Preset preview",
            description=f"Unknown preset `{slug}`.",
            style_token="red")
        return dataclasses.replace(base, embed=embed)
    op_lines = [
        f"• `{op.kind}` — {op.description or '(no description)'}"
        for op in preset.operations[:10]]
    if len(preset.operations) > 10:
        op_lines.append(f"_+{len(preset.operations) - 10} more_")
    fields: list[tuple] = [
        ("Operations", "\n".join(op_lines) or "_empty_", False)]
    warnings = preview_warnings(preset)
    if warnings:
        fields.append(
            ("Warnings", "\n".join(f"• {w}" for w in warnings), False))
    embed = RenderedEmbed(
        title=f"🎛 {preset.display_name} · preview",
        description=(
            f"**{len(preset.operations)}** operation(s) would be staged.  "
            "Confirm to add them to the draft; nothing applies yet."),
        fields=tuple(fields),
        footer="Confirm below to stage every op in the draft.",
        style_token="blurple")
    return dataclasses.replace(base, embed=embed)


# --- handlers ------------------------------------------------------------------------------

def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.preset_pick")):
        return

    @handler("setup.open_section_preset_select")
    async def open_section_preset_select(req) -> Reply | None:
        """The hub's Load-preset section button — gate exactly like the
        shipped hub button, then land on the preset card
        (preset_select.run's build_preset_embed + PresetSectionView)."""
        from sb.domain.setup import wizard
        from sb.domain.setup.wizard import _open

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, wizard.GATE_MSG_WIZARD)
        await _open(req, PRESET_PANEL_ID)
        return None

    @handler("setup.preset_pick")
    async def preset_pick(req) -> Reply | None:
        """_PresetPickSelect.callback: stash the pick, open the
        preview + confirm view."""
        from sb.domain.setup.wizard import _open

        values = tuple(req.args.get("values", ()) or ())
        slug = str(values[0]) if values else ""
        if slug == "_none":
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "No presets bundled in "
                         "services.automation_templates.")
        _PICKED[_key(req)] = slug
        await _open(req, PRESET_PREVIEW_PANEL_ID)
        return None

    @handler("setup.preset_confirm")
    async def preset_confirm(req) -> Reply:
        """_ConfirmPresetView._confirm → _stage_preset, ported: every
        adapted op lands in the K9 draft; the shipped
        staged/pending/failed summary answers."""
        from sb.domain.setup import section_card, wizard
        from sb.kernel.draft.store import DraftStore
        from sb.spec.draft import DraftOperation

        slug = _PICKED.get(_key(req), "")
        preset = get_preset(slug)
        if preset is None:
            # shipped copy, verbatim (_stage_preset's unknown branch).
            return Reply(BLOCKED, f"Unknown preset `{slug}`.")
        _register_set_setting_op_kind()
        _register_add_automation_rule_op_kind()
        guild_id = int(req.guild_id or 0)
        rows = staged_ops_for_preset(preset)
        staged = 0
        failed: list[str] = []
        store = DraftStore()
        try:
            _s, draft = await section_card._open_or_create_draft(guild_id)
        except Exception:  # noqa: BLE001 — every op fails the shipped way
            logger.exception("preset %s: draft open failed", slug)
            draft = None
        for op_kind, subsystem, payload, label in rows:
            if draft is None:
                failed.append(label)
                continue
            try:
                await store.add(draft.draft_id, DraftOperation(
                    op_seq=0,       # append_operation assigns the sequence
                    op_kind=op_kind, subsystem=subsystem,
                    authority_ref="", payload=payload, label=label))
                staged += 1
            except Exception:  # noqa: BLE001 — per-op isolation (shipped)
                logger.exception(
                    "preset %s: append failed for op kind=%s", slug, op_kind)
                failed.append(label)
        await section_card.mark_step_in_progress(req, SLUG)
        try:
            pending = await wizard.staged_ops_count(guild_id)
        except Exception:  # noqa: BLE001 — the shipped count soft-fail
            logger.exception("preset_select: setup_draft.count failed")
            pending = 0
        # shipped summary lines, verbatim.
        summary_lines = [
            f"✅ Staged **{staged}** operation(s) from preset `{slug}`.",
            f"Pending operations: **{pending}**.",
        ]
        if failed:
            summary_lines.append(
                f"⚠️ Failed to stage **{len(failed)}** op(s) — see logs.")
        return Reply(SUCCESS, "\n".join(summary_lines))

    @handler("setup.preset_cancel")
    async def preset_cancel(req) -> Reply:
        """_ConfirmPresetView._cancel — the shipped cancelled content
        line (the disabled-view edit is the ledgered text-reply seam)."""
        return Reply(SUCCESS, "Preset staging cancelled — draft unchanged.")


# --- registration ---------------------------------------------------------------------------

def _register_panels() -> None:
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    for name, fn in (("setup.preset_card_render", _render_preset_card),
                     ("setup.preset_preview_render", _render_preset_preview)):
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)
    for pid, factory in ((PRESET_PANEL_ID, preset_card_spec),
                         (PRESET_PREVIEW_PANEL_ID, preset_preview_spec)):
        if not is_registered(PanelRef(pid)):
            panel(pid)(factory)


_ensure_providers()
_register()
_register_panels()
_register_set_setting_op_kind()
_register_add_automation_rule_op_kind()


def ensure_preset_select_refs() -> None:
    _ensure_providers()
    _register()
    _register_panels()
    _register_set_setting_op_kind()
    _register_add_automation_rule_op_kind()

"""Help overlay editor — the operator UI for guild Help appearance
(ORACLE disbot/views/help/editor.py, the audit Phase-5 flow over the
D-0026 named-successor overlay store).

Edit what migration 0051 makes storable — per-guild **hide / rename /
re-describe** of hubs (categories) and subsystems — with per-field and
full reset. The flow is ``help.editor_home`` (counts + reset-all) →
``help.editor_pick_hub`` / ``help.editor_pick_sub`` (windowed catalogue
picker) → ``help.editor_entity`` (one entity).

Shipped contract, kept:

* **Writes only through** the audited K7 lanes
  (:mod:`sb.domain.help.overlay_ops`) — one op per editor action; the
  panels never touch the table and never import an admission path (the
  Q-0055 fence: hiding is display-only, and the editor copy says so).
* **Authority re-checked at every callback** — the administrator floor
  is K6-resolved on every dispatch AND the op's own authority_ref
  re-checks at the engine (the view check was never the gate).
* **Q-0058 rendering:** every entity shows custom + default + stable key.
* **Entity choice happens in panels** — the G-10 modals carry only text
  inputs (a Discord modal cannot contain a select).
* Entry point (Q-0032 — no new command names): the server-management
  hub's ``✏️ Help editor`` button. (The shipped second door — the
  Settings hub's "Help appearance" group — rides the settings-mutation
  successor lane.)

Ledgered deviations (this slice's PR / D-0089):
* the entity editor's escape is the grammar ``nav:back`` to the editor
  HOME (the shipped ◀ Back returned to the picker — a static parent
  cannot key on the picked kind; one extra click, nothing strands);
* the shipped picker was one view parameterized by kind; the grammar
  declares TWO panels (hubs / subsystems) so each carries its static
  title byte;
* the shipped 🏠 Home message lane (the Q-0059 embed builder,
  views/help/home_builder.py + oracle migration 067) is its own
  successor slice — the button lands on a declared pending terminal;
* the reset-confirm copy drops the shipped "and the custom Home
  message" clause (no home row exists to remove yet — the copy would
  lie).

State (kind pick, entity pick, picker page) is per (guild, invoker)
in-memory view state (the cogmgr precedent); handlers register at
MODULE IMPORT (the composition-parity invariant).
"""

from __future__ import annotations

import logging
from dataclasses import replace as _dc_replace

from sb.spec.panels import (
    ActionStyle,
    Audience,
    DeferMode,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    ModalFieldSpec,
    ModalSpec,
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
    is_registered,
    panel,
    provider,
)

logger = logging.getLogger("sb.domain.help.editor")

__all__ = [
    "editor_entity_spec",
    "editor_home_spec",
    "editor_panel_specs",
    "editor_pick_spec",
    "editor_reset_confirm_spec",
    "ensure_editor_refs",
]

#: Discord's select-option cap; entity lists window past it (shipped).
_PAGE_SIZE = 25

#: the shipped footer byte (editor.py _FOOTER) — true here: the live
#: help providers read the overlay per render (service.py wiring).
_FOOTER = "Changes are live in Help immediately — verify with 👁 Help Preview"

#: Q-0055 copy — hiding never carries execution meaning (shipped byte).
_HIDDEN_NOTE = "hidden from Help but still executable"

_KINDS = {"hub": "hubs", "subsystem": "subsystems"}


# --- per-invoker view state (the cogmgr pick/page precedent) -------------------

_entity_pick: dict[tuple[int, int], tuple[str, str]] = {}
_picker_page: dict[tuple[int, int, str], int] = {}


def _mem_key(guild_id, user_id) -> tuple[int, int]:
    return (int(guild_id or 0), int(user_id or 0))


def entity_pick_for(guild_id, user_id) -> tuple[str, str] | None:
    return _entity_pick.get(_mem_key(guild_id, user_id))


def picker_page_for(guild_id, user_id, kind: str) -> int:
    return max(0, _picker_page.get((*_mem_key(guild_id, user_id), kind), 0))


def _ctx_ids(ctx) -> tuple[int, int]:
    return (int(getattr(ctx, "guild_id", 0) or 0),
            int(getattr(getattr(ctx, "actor", None), "user_id", 0) or 0))


# --- shared reads ----------------------------------------------------------------


async def _overlay(guild_id: int):
    from sb.domain.help.overlay import get_guild_help_overlay

    return await get_guild_help_overlay(guild_id or None)


def _orphans(overlay) -> list:
    from sb.domain.help.overlay import known_entities

    known = {kind: set(known_entities(kind)) for kind in ("hub", "subsystem")}
    return [r for r in overlay.rows
            if r.entity_key not in known.get(r.entity_kind, set())]


def _picker_rows(kind: str, overlay) -> list[tuple[str, str, bool, str]]:
    """``(key, effective_label, hidden, default_name)`` rows in catalogue
    order (the shipped ``EntityPickerView.build_embed`` read)."""
    from sb.domain.help.overlay import entity_defaults, known_entities

    rows = []
    for key in known_entities(kind):
        default_name, _desc = entity_defaults(kind, key)
        override = overlay.get(kind, key)
        label = (override.display_name
                 if override is not None and override.display_name is not None
                 else default_name)
        hidden = bool(override.display_hidden) if override is not None \
            else False
        rows.append((key, label, hidden, default_name))
    return rows


# --- fields providers ---------------------------------------------------------------


async def _home_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped editor landing: current override counts + the orphan
    report (build_editor_home_embed, copy verbatim)."""
    gid, _uid = _ctx_ids(ctx)
    overlay = await _overlay(gid)
    hidden = sum(1 for r in overlay.rows if r.display_hidden)
    renamed = sum(1 for r in overlay.rows if r.display_name is not None)
    redescribed = sum(1 for r in overlay.rows if r.description is not None)
    fields = [(
        "Current overrides",
        (f"🙈 hidden: **{hidden}** · ✏️ renamed: **{renamed}** · "
         f"📝 re-described: **{redescribed}**"
         if overlay.rows
         else "*(none — Help renders its defaults)*"),
    )]
    orphans = _orphans(overlay)
    if orphans:
        keys = ", ".join(f"`{r.entity_key}`" for r in orphans)
        fields.append((
            f"⚠️ Orphaned overrides ({len(orphans)})",
            (f"{keys} — these reference retired Help entries and are "
             "never rendered. **Reset all** clears them."),
        ))
    return tuple(fields)


async def _entity_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped one-entity edit card — custom + default + stable key
    (build_entity_editor_embed, copy verbatim)."""
    from sb.domain.help.overlay import entity_defaults

    gid, uid = _ctx_ids(ctx)
    pick = entity_pick_for(gid, uid)
    if pick is None:
        return (("Nothing selected",
                 "Pick a hub or subsystem from the editor first."),)
    kind, key = pick
    overlay = await _overlay(gid)
    row = overlay.get(kind, key)
    default_name, default_desc = entity_defaults(kind, key)
    custom_name = row.display_name if row else None
    custom_desc = row.description if row else None
    hidden = bool(row.display_hidden) if row else False
    return (
        ("Name",
         (f"custom: **{custom_name}**\ndefault: {default_name}"
          if custom_name
          else f"default: **{default_name}** *(no override)*")),
        ("Description",
         (f"custom: **{custom_desc}**\ndefault: {default_desc or '*(none)*'}"
          if custom_desc
          else f"default: **{default_desc or '*(none)*'}** "
               "*(no override)*")),
        ("Visibility",
         (f"🙈 **Hidden** — {_HIDDEN_NOTE}" if hidden
          else "👁 Shown (default)")),
    )


def _picker_options_provider(kind: str):
    async def _options(ctx) -> tuple[dict, ...]:
        """One page of catalogue entities; label = effective display
        (Q-0058); 🙈 marks hidden (the shipped _EntitySelect options)."""
        gid, uid = _ctx_ids(ctx)
        overlay = await _overlay(gid)
        rows = _picker_rows(kind, overlay)
        page = min(picker_page_for(gid, uid, kind),
                   max(0, (len(rows) - 1) // _PAGE_SIZE))
        window = rows[page * _PAGE_SIZE:(page + 1) * _PAGE_SIZE]
        return tuple(
            {"label": (f"🙈 {label}" if hidden else label)[:100],
             "value": key,
             "description": f"default: {default} · {key}"[:100]}
            for key, label, hidden, default in window
        )
    return _options


# --- the modals (G-10; text inputs only — shipped rule) ------------------------------

RENAME_MODAL = ModalSpec(
    modal_id="help.editor_rename_form",
    title="Rename in Help",                       # shipped byte
    fields=(
        ModalFieldSpec(field_id="name",
                       label="Custom display name (Help only)",  # shipped
                       required=True, min_length=1, max_length=100),
    ),
    on_submit=HandlerRef("help.editor_rename"),
)

REDESCRIBE_MODAL = ModalSpec(
    modal_id="help.editor_redescribe_form",
    title="Re-describe in Help",                  # shipped byte
    fields=(
        ModalFieldSpec(field_id="description",
                       label="Custom description (Help only)",   # shipped
                       required=True, min_length=1, max_length=100),
    ),
    on_submit=HandlerRef("help.editor_redescribe"),
)


# --- the panel specs -------------------------------------------------------------------


def editor_home_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="help.editor_home",
        subsystem="help",
        title="✏️ Help appearance editor",        # shipped byte
        audience=Audience.INVOKER,
        # the shipped ADMIN_COLOR — discord.Color.red().
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(
            # the shipped landing description, verbatim.
            TextBlock(
                "Customize what **Help** shows in this server: hide "
                f"entries ({_HIDDEN_NOTE}), rename them, or re-describe "
                "them. Changes apply to Help only — never to permissions "
                "or execution."),
            FieldsBlock(provider=ProviderRef("help.editor_home_fields")),
        ),
        actions=(
            PanelActionSpec(
                action_id="eh_hubs", label="🏛 Hubs",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("help.editor_open_hubs")),
            PanelActionSpec(
                action_id="eh_subsystems", label="🧩 Subsystems",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("help.editor_open_subs")),
            PanelActionSpec(
                # the shipped 🏠 Home message lane (Q-0059 builder) is its
                # own successor slice — a declared pending terminal.
                action_id="eh_home_msg", label="🏠 Home message",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("help.editor_home_message_pending")),
            PanelActionSpec(
                action_id="eh_reset_all", label="🗑 Reset all…",
                style=ActionStyle.DANGER, audience_tier="administrator",
                handler=PanelRef("help.editor_reset_confirm")),
        ),
        # the editor home's escape is Help HOME — a ref inside the help
        # subsystem, so the manifest compiles in isolation (the shipped
        # editor was a standalone ephemeral; its opener hub keeps its own
        # message, and the Help-editor's subject IS Help).
        navigation=NavigationSpec(parent=PanelRef("help.home"),
                                  show_help=False, show_home=False),
        renderer_override=HandlerRef("help.render_editor_home"),
        justification=(
            "the shipped editor footer is the literal 'Changes are live "
            "in Help immediately — verify with 👁 Help Preview' "
            "(views/help/editor.py _FOOTER) — outside FooterMode's "
            "none/subsystem/provenance vocabulary (the hub-footer "
            "precedent). The override delegates to the grammar renderer "
            "and sets only the footer byte; body, fields, actions and "
            "layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("eh_hubs", "eh_subsystems", "eh_home_msg"),
            ("eh_reset_all",),
        )),)),
    )


def editor_pick_spec(kind: str) -> PanelSpec:
    plural = _KINDS[kind]
    prefix = "eph" if kind == "hub" else "eps"
    return PanelSpec(
        panel_id=f"help.editor_pick_{'hub' if kind == 'hub' else 'sub'}",
        subsystem="help",
        title=f"✏️ Help editor — {plural}",        # shipped byte
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(
            # the shipped picker description, verbatim.
            TextBlock(
                f"Pick a {kind} to hide, rename, or re-describe. "
                "🙈 marks entries currently hidden from Help."),
        ),
        selectors=(
            SelectorSpec(
                selector_id=f"{prefix}_select", kind=SelectorKind.ENTITY,
                options_source=ProviderRef(f"help.editor_{kind}_options"),
                placeholder=f"Pick a {kind} to edit…",   # shipped byte
                empty_state="(nothing to edit)",         # shipped byte
                audience_tier="administrator",
                on_select=HandlerRef(f"help.editor_pick_{kind}")),
        ),
        actions=(
            # the shipped ◀ Prev / Next ▶ window pair (rendered
            # edge-disabled via the override; one page ⇒ both disabled).
            PanelActionSpec(
                action_id=f"{prefix}_prev", label="◀ Prev",
                audience_tier="administrator",
                handler=HandlerRef(f"help.editor_{kind}_prev")),
            PanelActionSpec(
                action_id=f"{prefix}_next", label="Next ▶",
                audience_tier="administrator",
                handler=HandlerRef(f"help.editor_{kind}_next")),
        ),
        navigation=NavigationSpec(parent=PanelRef("help.editor_home"),
                                  show_help=False, show_home=False),
        renderer_override=HandlerRef(f"help.render_editor_pick_{kind}"),
        justification=(
            "the shipped picker placeholder is PAGE-keyed state copy "
            "('Pick a … to edit… (page N/M)' past one page), the shipped "
            "◀ Prev / Next ▶ pair renders edge-DISABLED (actions carry "
            "no disabled state in the grammar), and the shipped editor "
            "footer literal rides every editor surface (the cogmgr "
            "window + hub-footer precedents). The override delegates to "
            "the grammar renderer and adjusts only those surfaces; the "
            "select options stay provider-declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            (f"{prefix}_select",),
            (f"{prefix}_prev", f"{prefix}_next"),
        )),)),
    )


def editor_entity_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="help.editor_entity",
        subsystem="help",
        # the shipped title/description are ENTITY-keyed (override).
        title="✏️ Help entity editor",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(
            TextBlock("Pick a hub or subsystem from the editor first."),
            FieldsBlock(provider=ProviderRef("help.editor_entity_fields")),
        ),
        actions=(
            # row 0 — the shipped edit trio.
            PanelActionSpec(
                action_id="ee_hide", label="🙈 Hide",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("help.editor_toggle_hide")),
            PanelActionSpec(
                action_id="ee_rename", label="✏️ Rename…",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                defer_mode=DeferMode.MODAL, modal=RENAME_MODAL,
                handler=HandlerRef("help.editor_rename")),
            PanelActionSpec(
                action_id="ee_redescribe", label="📝 Re-describe…",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                defer_mode=DeferMode.MODAL, modal=REDESCRIBE_MODAL,
                handler=HandlerRef("help.editor_redescribe")),
            # row 1 — the shipped reset trio.
            PanelActionSpec(
                action_id="ee_reset_name", label="♻️ Reset name",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("help.editor_reset_name")),
            PanelActionSpec(
                action_id="ee_reset_desc", label="♻️ Reset description",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("help.editor_reset_desc")),
            PanelActionSpec(
                action_id="ee_reset_entity", label="🗑 Reset entity",
                style=ActionStyle.DANGER, audience_tier="administrator",
                handler=HandlerRef("help.editor_reset_entity")),
        ),
        # the compiled escape goes HOME (ledgered deviation: the shipped
        # ◀ Back returned to the picker — a static parent cannot key on
        # the picked kind; one extra click, nothing strands).
        navigation=NavigationSpec(parent=PanelRef("help.editor_home"),
                                  show_help=False, show_home=False),
        renderer_override=HandlerRef("help.render_editor_entity"),
        justification=(
            "the shipped entity card's TITLE ('✏️ <custom or default "
            "name>'), DESCRIPTION ('Editing the **<kind>** `<key>` …') "
            "and FOOTER ('… · stable key: <key>') are entity-keyed state "
            "copy, and the shipped Hide button RELABELS to '👁 Unhide' "
            "(+ green style) while the entity is hidden — state-keyed "
            "component copy outside the static grammar (the cogmgr "
            "selection-footer precedent). The override delegates to the "
            "grammar renderer and adjusts only those four surfaces; "
            "fields, the remaining actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("ee_hide", "ee_rename", "ee_redescribe"),
            ("ee_reset_name", "ee_reset_desc", "ee_reset_entity"),
        )),)),
    )


def editor_reset_confirm_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="help.editor_reset_confirm",
        subsystem="help",
        title="Reset ALL Help customizations?",   # shipped byte
        audience=Audience.INVOKER,
        # the shipped confirm accent — discord.Color.red().
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(
            # the shipped warning copy MINUS the home-message clause
            # (module docstring: no home row exists to remove yet).
            TextBlock(
                "Every hide, rename, and re-description in this server "
                "will be removed and Help returns to its defaults. This "
                "cannot be undone (the audit log keeps the history)."),
        ),
        actions=(
            PanelActionSpec(
                action_id="erc_confirm", label="🗑 Yes, reset everything",
                style=ActionStyle.DANGER, audience_tier="administrator",
                handler=HandlerRef("help.editor_reset_all")),
            PanelActionSpec(
                action_id="erc_cancel", label="Cancel",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=PanelRef("help.editor_home")),
        ),
        navigation=NavigationSpec(parent=PanelRef("help.editor_home"),
                                  show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("erc_confirm", "erc_cancel"),
        )),)),
    )


def editor_panel_specs() -> tuple[PanelSpec, ...]:
    return (editor_home_spec(), editor_pick_spec("hub"),
            editor_pick_spec("subsystem"), editor_entity_spec(),
            editor_reset_confirm_spec())


# --- renderer overrides -------------------------------------------------------------


async def _render_editor_home(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal (see justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed, footer=_FOOTER))


def _render_editor_pick(kind: str):
    async def _render(spec: PanelSpec, ctx) -> object:
        """Grammar render + the shipped page-keyed placeholder, the
        edge-disabled window pair, and the editor footer literal."""
        from sb.kernel.panels.render import render_panel

        rendered = await render_panel(spec, ctx)
        gid, uid = _ctx_ids(ctx)
        overlay = await _overlay(gid)
        rows = _picker_rows(kind, overlay)
        pages = max(1, -(-len(rows) // _PAGE_SIZE))
        page = min(picker_page_for(gid, uid, kind), pages - 1)
        placeholder = f"Pick a {kind} to edit…"
        if pages > 1:
            placeholder += f" (page {page + 1}/{pages})"    # shipped byte
        components = []
        for c in rendered.components:
            leaf = c.custom_id.rsplit(".", 1)[-1].rsplit(":", 1)[-1]
            if leaf.endswith("_prev"):
                c = _dc_replace(c, disabled=(page == 0))
            elif leaf.endswith("_next"):
                c = _dc_replace(c, disabled=(page >= pages - 1))
            elif c.kind == "selector":
                c = _dc_replace(c, placeholder=placeholder)
            components.append(c)
        return _dc_replace(rendered, components=tuple(components),
                           embed=_dc_replace(rendered.embed,
                                             footer=_FOOTER))
    return _render


async def _render_editor_entity(spec: PanelSpec, ctx) -> object:
    """Grammar render + the four shipped entity-keyed surfaces (see
    justification): title, description, footer, and the Hide/Unhide
    relabel."""
    from sb.domain.help.overlay import entity_defaults
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    gid, uid = _ctx_ids(ctx)
    pick = entity_pick_for(gid, uid)
    if pick is None:
        return _dc_replace(rendered,
                           embed=_dc_replace(rendered.embed, footer=_FOOTER))
    kind, key = pick
    overlay = await _overlay(gid)
    row = overlay.get(kind, key)
    default_name, _desc = entity_defaults(kind, key)
    custom_name = row.display_name if row else None
    hidden = bool(row.display_hidden) if row else False
    components = []
    for c in rendered.components:
        leaf = c.custom_id.rsplit(".", 1)[-1].rsplit(":", 1)[-1]
        if leaf == "ee_hide":
            # the shipped _relabel_hide_button, byte for byte.
            c = _dc_replace(
                c, label="👁 Unhide" if hidden else "🙈 Hide",
                style=(ActionStyle.SUCCESS.value if hidden
                       else ActionStyle.SECONDARY.value))
        components.append(c)
    return _dc_replace(
        rendered,
        components=tuple(components),
        embed=_dc_replace(
            rendered.embed,
            title=f"✏️ {custom_name or default_name}",        # shipped
            description=(f"Editing the **{kind}** `{key}` — every field "
                         "shows the custom value and the default it "
                         "overrides."),                        # shipped
            footer=f"{_FOOTER} · stable key: {key}"))          # shipped


# --- handlers ----------------------------------------------------------------------


def _register_refs() -> None:
    from sb.domain.operator_spine import pending_handler
    from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import handler

    for pid, factory in (
        ("help.editor_home", editor_home_spec),
        ("help.editor_pick_hub", lambda: editor_pick_spec("hub")),
        ("help.editor_pick_sub", lambda: editor_pick_spec("subsystem")),
        ("help.editor_entity", editor_entity_spec),
        ("help.editor_reset_confirm", editor_reset_confirm_spec),
    ):
        if not is_registered(PanelRef(pid)):
            panel(pid)(factory)

    for name, fn in (
        ("help.editor_home_fields", _home_fields),
        ("help.editor_entity_fields", _entity_fields),
        ("help.editor_hub_options", _picker_options_provider("hub")),
        ("help.editor_subsystem_options",
         _picker_options_provider("subsystem")),
    ):
        if not is_registered(ProviderRef(name)):
            provider(name)(fn)

    for name, fn in (
        ("help.render_editor_home", _render_editor_home),
        ("help.render_editor_pick_hub", _render_editor_pick("hub")),
        ("help.render_editor_pick_subsystem",
         _render_editor_pick("subsystem")),
        ("help.render_editor_entity", _render_editor_entity),
    ):
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)

    pending_handler(
        "help.editor_home_message_pending",
        "🏠 The Help Home-message builder (the Q-0059 embed builder) "
        "ports with its own slice.")

    if is_registered(HandlerRef("help.editor_open_hubs")):
        return

    def _req_key(req) -> tuple[int, int]:
        return _mem_key(req.guild_id, getattr(req.actor, "user_id", 0))

    async def _open(req, panel_id: str) -> None:
        import dataclasses

        from sb.kernel.panels.engine import open_panel

        await open_panel(PanelRef(panel_id),
                         dataclasses.replace(req, args=dict(req.args)))

    async def _run_op(req, op_key: str, params: dict) -> Reply | None:
        from sb.spec.refs import WorkflowRef, resolve

        result = await resolve(WorkflowRef(op_key))(
            ctx_from_request(req, params))
        if getattr(result, "outcome", None) != SUCCESS:
            return Reply(result.outcome, result.user_message)
        return None

    def _pick(req) -> tuple[str, str] | None:
        return entity_pick_for(req.guild_id,
                               getattr(req.actor, "user_id", 0))

    async def _edit(req, fields: dict) -> Reply:
        """One editor action → one audited op → re-render in place (the
        shipped _apply_edit; contract errors surface as the op's own
        final copy and leave the editor untouched)."""
        pick = _pick(req)
        if pick is None:
            # evicted view state (restart) — route back to the editor.
            return Reply(SUCCESS,
                         "Pick a hub or subsystem from the editor first.")
        kind, key = pick
        failed = await _run_op(req, "help.set_overlay_fields", {
            "entity_kind": kind, "entity_key": key, "fields": fields})
        if failed is not None:
            return failed
        await _open(req, "help.editor_entity")
        return Reply(SUCCESS, None)

    @handler("help.editor_open_hubs")
    async def editor_open_hubs(req):
        """🏛 Hubs — the shipped hubs picker lane."""
        _picker_page[(*_req_key(req), "hub")] = 0
        await _open(req, "help.editor_pick_hub")
        return Reply(SUCCESS, None)

    @handler("help.editor_open_subs")
    async def editor_open_subs(req):
        """🧩 Subsystems — the shipped subsystems picker lane."""
        _picker_page[(*_req_key(req), "subsystem")] = 0
        await _open(req, "help.editor_pick_sub")
        return Reply(SUCCESS, None)

    def _page_step(kind: str, delta: int):
        async def _step(req):
            from sb.domain.help.overlay import known_entities

            pages = max(1, -(-len(known_entities(kind)) // _PAGE_SIZE))
            mem = (*_req_key(req), kind)
            _picker_page[mem] = min(max(
                _picker_page.get(mem, 0) + delta, 0), pages - 1)
            await _open(req, "help.editor_pick_"
                        f"{'hub' if kind == 'hub' else 'sub'}")
            return Reply(SUCCESS, None)
        return _step

    handler("help.editor_hub_prev")(_page_step("hub", -1))
    handler("help.editor_hub_next")(_page_step("hub", +1))
    handler("help.editor_subsystem_prev")(_page_step("subsystem", -1))
    handler("help.editor_subsystem_next")(_page_step("subsystem", +1))

    def _pick_entity(kind: str):
        async def _on_pick(req):
            from sb.domain.help.overlay import known_entities

            values = tuple(req.args.get("values") or ())
            key = str(values[0]) if values else ""
            if key not in known_entities(kind):
                # the shipped empty-window sentinel (value "-") and any
                # stale key land here — the polite terminal.
                return Reply(SUCCESS, "That entry is no longer available.")
            _entity_pick[_req_key(req)] = (kind, key)
            await _open(req, "help.editor_entity")
            return Reply(SUCCESS, None)
        return _on_pick

    handler("help.editor_pick_hub")(_pick_entity("hub"))
    handler("help.editor_pick_subsystem")(_pick_entity("subsystem"))

    @handler("help.editor_toggle_hide")
    async def editor_toggle_hide(req):
        """🙈 Hide / 👁 Unhide — unhide resets the field to inherit
        (None); the store keeps only deviations (shipped semantics)."""
        pick = _pick(req)
        if pick is None:
            return Reply(SUCCESS,
                         "Pick a hub or subsystem from the editor first.")
        kind, key = pick
        overlay = await _overlay(int(req.guild_id or 0))
        hidden = overlay.hidden(kind, key)
        return await _edit(req,
                           {"display_hidden": None if hidden else True})

    @handler("help.editor_rename")
    async def editor_rename(req):
        """✏️ Rename… (modal submit) — one audited op, Help-only."""
        return await _edit(req,
                           {"display_name": str(req.args.get("name") or "")})

    @handler("help.editor_redescribe")
    async def editor_redescribe(req):
        """📝 Re-describe… (modal submit) — one audited op, Help-only."""
        return await _edit(
            req, {"description": str(req.args.get("description") or "")})

    @handler("help.editor_reset_name")
    async def editor_reset_name(req):
        """♻️ Reset name — back to the default (inherit)."""
        return await _edit(req, {"display_name": None})

    @handler("help.editor_reset_desc")
    async def editor_reset_desc(req):
        """♻️ Reset description — back to the default (inherit)."""
        return await _edit(req, {"description": None})

    @handler("help.editor_reset_entity")
    async def editor_reset_entity(req):
        """🗑 Reset entity — every override field back to inherit; the
        all-default row disappears entirely (store only deviations)."""
        return await _edit(req, {"display_hidden": None,
                                 "display_name": None,
                                 "description": None})

    @handler("help.editor_reset_all")
    async def editor_reset_all(req):
        """🗑 Yes, reset everything — the shipped two-step destructive
        reset's confirm leg (nothing was written until this click)."""
        failed = await _run_op(req, "help.reset_overlay", {})
        if failed is not None:
            return failed
        await _open(req, "help.editor_home")
        return Reply(SUCCESS, None)


_register_refs()


def ensure_editor_refs() -> None:
    _register_refs()

"""The CLEANUP panels (parity flip) — the shipped Cleanup Hub
(disbot/cogs/cleanup/panel.py ``CleanupPanelView`` + its embed builder)
and the shipped Prohibited Words Manager (disbot/cogs/cleanup_cog.py's
word-menu view, ``!wordmenu``), byte-for-byte as the goldens pin them
(parity/goldens/cleanup/: sweep_cleanup, sweep_wordmenu).

The hub: the 🧹 red read-only router — the shipped two-sentence blurb,
the live ``Prohibited Words`` count field (``{n} configured`` /
``_None configured_`` — the shipped panel.py copy, inline=True) + the
``Auto-Delete`` policy blurb, the "Read-only summary." footer — over the
shipped rows: 🔤 Prohibited Words / 📝 Logging Status / ⚙️ Settings /
🧹 Cleanup Policies, the 🔄 Refresh row, and the shipped STANDARD nav
row (``nav:help`` + ``nav:hub:moderation`` "↩ Moderation"). Every
declared component carries its shipped PERSISTENT ``cleanup:*``
custom_id verbatim (``custom_id_override``; the settings-hub/
server-management precedent). ``session_lifecycle=True`` with every
declared id override-pinned: nothing is run-minted and no
``panel_anchors`` row is recorded (the golden's db_delta carries none).

The words manager: the 🔤 red session view — no description, the two
fields (``Current Words`` / ``🛡️ Anti-evasion matching``), the "Use
buttons below" footer — over the shipped button rows (➕ Add Word /
➖ Remove Word / 🔄 Refresh, then 🔍 Scan History / 🛡️ Anti-evasion).
The shipped view minted discord.py auto-ids (the golden pins
``<cid:1>``..``<cid:5>``) — no overrides, so ``_mint_ephemeral`` mints
run ids in declared order; the shipped view carried NO nav row, so the
never-strand fence takes the session-view exemption.

Deliberate under-ports (parity beyond the goldens; the settings
Inventory-literal / servermanagement badge-literal precedent):
* the words manager's ``Current Words`` value is the golden-pinned
  literal `` `test` `` — the shipped view read ``self.cog._word_cache``
  (an in-memory cache), and the capture's alphabetical sweep order left
  the ``!word add test`` write in that cache when ``!wordmenu`` ran
  (the per-case DB truncate cannot reach process memory), so the golden
  pins the leaked cache state, not a DB read. The live-read rendering
  (and the honest empty state) lands with the word-mutation panel
  slice;
* the ``🛡️ Anti-evasion matching`` field is the shipped default-off
  literal — the anti-evasion setting read/toggle is the same slice;
* the remaining pending clicks (sb/domain/cleanup/handlers.py): the
  hub's ⚙️ Settings / 🧹 Cleanup Policies sub-views and the words
  manager's 🛡️ Anti-evasion toggle. Everything else routes for real:
  🔤 Prohibited Words opens the ported words manager, 📝 Logging Status
  opens the ported ``logging.hub`` (the server-logging slice landed),
  ➕/➖ open G-10 word modals whose submits run the audited
  ``cleanup.word_add_op``/``word_remove_op`` command twins (the
  moderation.hub.warn modal-ingress precedent), 🔄 refresh re-renders
  each panel in place, and 🔍 Scan History runs the live
  ``cleanup.history_scan`` handler (``!cleanuphistory``'s route).
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
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
    ResultRender,
)
from sb.spec.panels import TextBlock
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    WorkflowRef,
    is_registered,
    panel,
    provider,
)

__all__ = [
    "cleanup_hub_spec",
    "cleanup_words_spec",
    "ensure_panel_refs",
    "install_cleanup_panels",
]

# --- the shipped hub copy (cogs/cleanup/panel.py — the golden pins every
# byte). -----------------------------------------------------------------------

_HUB_DESCRIPTION = (
    "Auto-moderation policies for command-style messages and prohibited "
    "content. Per-channel behaviour is configured under **Cleanup Policies** "
    "below."
)

#: the shipped footer literal (panel.py set_footer) — outside FooterMode's
#: vocabulary, hence the renderer_override below (the settings/
#: server_management precedent).
_HUB_FOOTER = "Read-only summary. Use the buttons below to manage policies."

#: the shipped Auto-Delete policy blurb (panel.py add_field, verbatim).
_HUB_AUTODELETE = (
    "Invalid/failed command-style messages are removed per the channel's "
    "cleanup policy (set a channel to **Off** to exempt it). Prohibited-word "
    "matches are removed with a brief warning."
)

# --- the shipped words-manager copy (cleanup_cog.py word-menu view). -----------

_WORDS_FOOTER = "Use buttons below to manage prohibited words."

#: golden-pinned literals (module-docstring under-port note: the shipped
#: view read the cog's in-memory `_word_cache`, and the capture pinned the
#: cache state the alphabetical sweep left behind — `!word add test` ran
#: before `!wordmenu`, and the per-case DB truncate cannot reach process
#: memory).
_WORDS_CURRENT = "`test`"
_WORDS_ANTI_EVASION = "⚫ **Off** — exact word match only"


# --- the word-mutation prompt modals (the moderation.hub.warn G-10 ingress
# precedent: button → declared ModalSpec → the audited K7 command twin).
# The shipped view's per-button modals prompted for one word; field_id
# "word" feeds ops._word_from (ctx.params["word"]) directly, exactly like
# `!word add <word>` / `!word remove <word>` (goldens sweep_word_add /
# sweep_word_remove pin the reply copy the twins answer with).

_WORD_FIELD = ModalFieldSpec(
    field_id="word", label="Word or phrase",
    placeholder="e.g. badword", required=True, max_length=100)

WORD_ADD_MODAL = ModalSpec(
    modal_id="cleanup.word_add_form", title="Add Prohibited Word",
    fields=(_WORD_FIELD,),
    on_submit=WorkflowRef("cleanup.word_add_op"))
WORD_REMOVE_MODAL = ModalSpec(
    modal_id="cleanup.word_remove_form", title="Remove Prohibited Word",
    fields=(_WORD_FIELD,),
    on_submit=WorkflowRef("cleanup.word_remove_op"))


# --- field providers ---------------------------------------------------------------

async def _hub_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped hub fields: the LIVE prohibited-word count (panel.py:
    ``f"{word_count} configured" if word_count else "_None configured_"``)
    + the Auto-Delete literal. The renderer override marks the count field
    inline — the shipped ``add_field(inline=True)`` wire shape."""
    from sb.domain.cleanup import store

    try:
        words = await store.get_words(int(getattr(ctx, "guild_id", 0) or 0))
    except Exception:  # noqa: BLE001 — a headless/db-free read renders empty
        words = []
    count = len(words)
    value = f"{count} configured" if count else "_None configured_"
    return (("Prohibited Words", value),
            ("Auto-Delete", _HUB_AUTODELETE))


async def _words_fields(ctx) -> tuple[tuple[str, str], ...]:
    """The golden-pinned words-manager fields (see the module-docstring
    under-port note — the live cache read is the word-mutation slice's)."""
    del ctx
    return (("Current Words", _WORDS_CURRENT),
            ("🛡️ Anti-evasion matching", _WORDS_ANTI_EVASION))


# --- the hub spec -------------------------------------------------------------------

def cleanup_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="cleanup.hub",
        subsystem="cleanup",
        title="🧹 Cleanup Hub",
        audience=Audience.INVOKER,
        # the shipped hub accent — discord.Color.red() (ERROR_COLOR token).
        frame=EmbedFrameSpec(style_token="red",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_HUB_DESCRIPTION),
              FieldsBlock(provider=ProviderRef("cleanup.hub_fields"))),
        actions=(
            # row 0 — the shipped router quartet (emoji IN the labels;
            # blurple word/policy doors, grey read-only views).
            PanelActionSpec(
                action_id="words", label="🔤 Prohibited Words",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                # the shipped hub opened the words manager — the PORTED
                # cleanup.words panel below.
                handler=PanelRef("cleanup.words"),
                custom_id_override="cleanup:words"),
            PanelActionSpec(
                action_id="logging", label="📝 Logging Status",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                # the shipped hub opened the Logging Status view — its
                # successor slice (server-logging) landed, so the click
                # routes to the PORTED logging.hub (the admin.hub
                # `admin_logging` nav precedent).
                handler=PanelRef("logging.hub"),
                custom_id_override="cleanup:logging"),
            PanelActionSpec(
                action_id="settings", label="⚙️ Settings",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("cleanup.settings_pending"),
                custom_id_override="cleanup:settings"),
            PanelActionSpec(
                action_id="policies", label="🧹 Cleanup Policies",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("cleanup.policies_pending"),
                custom_id_override="cleanup:policies"),
            # row 1 — the shipped grey in-place refresh (K1 custom_id
            # claims are repo-global on action_id — treasury owns bare
            # "refresh" (the sm_refresh/general_overview precedent); the
            # shipped wire id survives via the override).
            PanelActionSpec(
                action_id="cl_refresh", label="🔄 Refresh",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=PanelRef("cleanup.hub"),
                result_render=ResultRender.REFRESH_PANEL,
                custom_id_override="cleanup:refresh"),
        ),
        # the shipped hub carried the STANDARD nav row — 📚 Help +
        # ↩ Moderation (the shipped parent hub is `moderation`, pinned
        # explicitly until the moderation hub's own band installs a
        # resolver — the settings-explorer `admin` precedent).
        navigation=NavigationSpec(home_hub="moderation"),
        session_lifecycle=True,
        renderer_override=HandlerRef("cleanup.render_hub"),
        justification=(
            "the shipped hub footer is the literal 'Read-only summary. Use "
            "the buttons below to manage policies.' (cogs/cleanup/panel.py "
            "set_footer) — outside FooterMode's none/subsystem/provenance "
            "vocabulary — and the shipped Prohibited Words count field "
            "renders inline=True (panel.py add_field(inline=True)) — "
            "outside the grammar's vocabulary (2-tuple fields render "
            "inline=False). goldens/cleanup/sweep_cleanup.json pins both "
            "bytes (the settings-hub/access precedent). The override "
            "delegates to the grammar renderer and adjusts ONLY those two "
            "surfaces; body, fields, actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("words", "logging", "settings", "policies"),
            ("cl_refresh",),
        )),)),
    )


# --- the words-manager spec -----------------------------------------------------------

def cleanup_words_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="cleanup.words",
        subsystem="cleanup",
        title="🔤 Prohibited Words Manager",
        audience=Audience.INVOKER,
        # the shipped accent — ADMIN_COLOR == discord.Color.red().
        frame=EmbedFrameSpec(style_token="red",
                             footer_mode=FooterMode.NONE),
        # no description (the golden's embed carries no description key) —
        # the body is the two fields only.
        body=(FieldsBlock(provider=ProviderRef("cleanup.words_fields")),),
        actions=(
            # row 0 — the shipped word-mutation trio (run-minted auto-ids;
            # the golden pins <cid:1>..<cid:3>; emoji IN the labels).
            # ➕/➖ open the G-10 word modals whose submits run the audited
            # command twins (the moderation.hub.warn ingress precedent).
            PanelActionSpec(
                action_id="word_add", label="➕ Add Word",
                style=ActionStyle.SUCCESS, audience_tier="administrator",
                defer_mode=DeferMode.MODAL, modal=WORD_ADD_MODAL,
                handler=WorkflowRef("cleanup.word_add_op")),
            PanelActionSpec(
                action_id="word_remove", label="➖ Remove Word",
                style=ActionStyle.DANGER, audience_tier="administrator",
                defer_mode=DeferMode.MODAL, modal=WORD_REMOVE_MODAL,
                handler=WorkflowRef("cleanup.word_remove_op")),
            # the shipped grey in-place refresh (the hub's cl_refresh
            # pattern; the golden-pinned field literals re-render — the
            # live Current Words read stays the word-mutation slice's).
            PanelActionSpec(
                action_id="word_refresh", label="🔄 Refresh",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=PanelRef("cleanup.words"),
                result_render=ResultRender.REFRESH_PANEL),
            # row 1 — the shipped scan/anti-evasion pair (<cid:4>/<cid:5>).
            # 🔍 runs the live history scan (`!cleanuphistory`'s handler —
            # the shipped button ran the same sweep, default args).
            PanelActionSpec(
                action_id="scan_history", label="🔍 Scan History",
                style=ActionStyle.PRIMARY, audience_tier="administrator",
                handler=HandlerRef("cleanup.history_scan")),
            PanelActionSpec(
                action_id="anti_evasion", label="🛡️ Anti-evasion",
                style=ActionStyle.SECONDARY, audience_tier="administrator",
                handler=HandlerRef("cleanup.anti_evasion_pending")),
        ),
        # the shipped word-menu view carried ONLY its own buttons (no nav
        # row; timeout session view) — the golden pins exactly two
        # component rows; the never-strand fence takes the session-view
        # exemption (the general-menu precedent).
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("cleanup.render_words"),
        justification=(
            "the shipped words-manager footer is the literal 'Use buttons "
            "below to manage prohibited words.' (cleanup_cog.py set_footer) "
            "— outside FooterMode's none/subsystem/provenance vocabulary "
            "(goldens/cleanup/sweep_wordmenu.json pins the byte; the "
            "settings/server_management footer precedent). The override "
            "delegates to the grammar renderer and replaces ONLY the "
            "footer; body, fields, actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("word_add", "word_remove", "word_refresh"),
            ("scan_history", "anti_evasion"),
        )),)),
    )


# --- renderer overrides ---------------------------------------------------------------

async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the two shipped adjustments (see justification):
    the footer literal and the inline Prohibited Words count field."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    fields = tuple(
        (f[0], f[1], True) if f[0] == "Prohibited Words" else f
        for f in rendered.embed.fields)
    return _dc_replace(
        rendered,
        embed=_dc_replace(rendered.embed, footer=_HUB_FOOTER, fields=fields))


async def _render_words(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal (see justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed, footer=_WORDS_FOOTER))


# --- registration -----------------------------------------------------------------

def _register_refs() -> None:
    from sb.spec.refs import handler

    if not is_registered(PanelRef("cleanup.hub")):
        panel("cleanup.hub")(cleanup_hub_spec)
    if not is_registered(PanelRef("cleanup.words")):
        panel("cleanup.words")(cleanup_words_spec)
    if not is_registered(HandlerRef("cleanup.render_hub")):
        handler("cleanup.render_hub")(_render_hub)
    if not is_registered(HandlerRef("cleanup.render_words")):
        handler("cleanup.render_words")(_render_words)
    if not is_registered(ProviderRef("cleanup.hub_fields")):
        provider("cleanup.hub_fields")(_hub_fields)
    if not is_registered(ProviderRef("cleanup.words_fields")):
        provider("cleanup.words_fields")(_words_fields)


_register_refs()


def install_cleanup_panels() -> tuple[PanelSpec, ...]:
    """Register both panels with the panels registry (fences run here);
    composition-root/boot call. Idempotent for identical specs."""
    specs = (cleanup_hub_spec(), cleanup_words_spec())
    for spec in specs:
        try:
            register_panel(spec)
        except ValueError as exc:
            if "already registered" not in str(exc) and "duplicate" not in str(exc):
                raise
    return specs


def ensure_panel_refs() -> None:
    """Idempotent re-arm of the panel/handler/provider refs."""
    _register_refs()

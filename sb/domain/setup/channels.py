"""The CHANNELS & LOG ROUTING section flow (the section-flows slice),
ported from the oracle (menno420/superbot, read from the LOCAL oracle
clone: views/setup/sections/channels.py):

* the SECTION CARD entry (``run`` → section_card.show): the shared
  four-button card with the shipped ``detected_state`` copy; opening
  the section records the step marker (``mark_in_progress``);
* the DETAIL PICKER (``_customize_run`` + ``build_channels_embed``,
  bytes verbatim): every declared ``BindingSpec(kind=CHANNEL)`` across
  all registered subsystems, grouped by subsystem with the
  likely-match hint; the binding select opens the native channel
  picker; a pick stages a ``bind_channel`` row in the guild's K9
  draft — nothing applies until Final Review;
* APPLY RECOMMENDED (``_recommended_channel_ops``): stages a
  ``bind_channel`` op for every HIGH-confidence recommendation;
  medium/low picks are intentionally skipped (not safe to auto-stage
  without operator confirmation) but still surface as embed hints.

Kernel-idiom divergences, ledgered (the section_card.py doctrine):

* the binding walk reads the MANIFEST BindingSpec facets (the
  guild_snapshot._collect_bindings_snapshot precedent) — this
  architecture's ``all_schemas()`` twin;
* the recommendation source is the NATIVE RECOMMENDER
  (sb/domain/setup/recommender.py — the oracle
  ``channel_recommender.top_pick`` port: intent catalogue + perms
  scoring over the perms-bearing guild snapshot,
  sb/domain/platform/guild_snapshot.snapshot_for; the discord
  adapter's setup_reads fill arms it live) with the DETERMINISTIC
  ADVISOR (sb/domain/setup/plan.py — the same reproducible run
  ``/setup-describe`` takes) as the snapshot-less fallback lane —
  the formerly-flagged full-recommender follow-up, landed;
* at 21 declared channel bindings the one select carries every option
  (page_size 25); the oracle's windowed ◀/▶ select guarded the >25
  case — the pagination rides the engine's page_size lane when the
  count grows;
* the native channel picker's dynamic placeholder
  (``Pick a channel for {subsystem}.{binding}``) is patched onto the
  rendered component; the picker renders only after a binding is
  picked (the flow-state-dependent control — the final-review
  Apply-drop precedent);
* the manual pick's staging is GATED on the ported can_apply ladder
  (the card's "stage or skip" copy) — the oracle's ungated
  ``_stage_channel_binding`` predates the card's per-button re-check,
  additive fence, flagged;
* staged rows carry no oracle metadata dict (source=scan/manual,
  confidence, risk) — the final_review.py ledger note's class.

NO GOLDEN drives any of these components (the panels.py module pin);
the oracle SOURCES pin the copy, and every golden-pinned OPEN render
stays byte-identical.
"""

from __future__ import annotations

import logging

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = [
    "CHANNELS_DETAIL_PANEL_ID",
    "all_channel_bindings",
    "build_channels_embed_fields",
    "channels_detail_spec",
    "ensure_channels_refs",
    "recommended_channel_ops",
    "reset_channels_state_for_tests",
]

logger = logging.getLogger("sb.domain.setup")

SLUG = "channels"

CHANNELS_DETAIL_PANEL_ID = "setup.channels_detail"

_BINDING_OPTIONS_PROVIDER = "setup.channels_binding_options"

#: shipped glyphs, verbatim (channels._CONFIDENCE_GLYPH).
_CONFIDENCE_GLYPH: dict[str, str] = {
    "high": "✅",
    "medium": "🟡",
    "low": "⬜",
}

#: the shipped card copy, verbatim (channels.run's ``detected``).
_DETECTED_STATE = (
    "Channel-binding recommendations are computed live from the "
    "guild snapshot. Apply Recommended only stages high-confidence "
    "picks; use Customize to choose manually.")


# --- binding discovery (the manifest BindingSpec walk) ----------------------------------

def all_channel_bindings() -> list[tuple[str, str, bool, str]]:
    """(subsystem, name, required, hint) for every declared CHANNEL
    binding — the oracle ``_all_channel_bindings`` over this
    architecture's manifest facets."""
    import importlib
    import pkgutil

    import sb.manifest as manifest_pkg
    from sb.spec.settings import BindingKind, BindingSpec

    out: list[tuple[str, str, bool, str]] = []
    for info in sorted(pkgutil.iter_modules(manifest_pkg.__path__),
                       key=lambda i: i.name):
        try:
            mod = importlib.import_module(f"sb.manifest.{info.name}")
        except Exception:  # noqa: BLE001 — defensive per-module
            logger.exception("channels: manifest import failed (%s)",
                             info.name)
            continue
        manifest = getattr(mod, "MANIFEST", None)
        if manifest is None:
            continue
        for spec in getattr(manifest, "settings", ()) or ():
            if isinstance(spec, BindingSpec) and spec.kind is BindingKind.CHANNEL:
                out.append((str(manifest.key), spec.name,
                            bool(spec.required), str(spec.hint or "")))
    return out


# --- the recommendation read (recommender-first, advisor fallback) -------------------------

async def _recommendations(guild_id: int) -> dict[tuple[str, str], object]:
    """(subsystem, binding_name) → the top recommendation.

    RECOMMENDER lane (the native port, this slice): when the
    perms-bearing snapshot source is armed
    (sb/adapters/discord/setup_reads.py → guild_snapshot.snapshot_for),
    every declared binding with an intent mapping reads
    ``recommender.top_pick`` — the oracle ``_recommendation_for``
    consumer over ``channel_recommender.top_pick``; the pick is folded
    onto the advisor's SetupRecommendation shape (reason =
    ``reasons[0]``, the oracle embed's "strongest single reason for
    compactness").

    ADVISOR fallback (the pre-port lane, kept verbatim): a snapshot-less
    runtime (parity harness, headless tests) reads the deterministic
    advisor — hints degrade, never a crash."""
    from sb.domain.setup import plan, recommender

    snapshot = None
    try:
        from sb.domain.platform.guild_snapshot import snapshot_for

        snapshot = await snapshot_for(int(guild_id))
    except Exception:  # noqa: BLE001 — hints simply do not appear
        logger.exception("channels: snapshot lookup raised")
    if snapshot is not None:
        recs: dict[tuple[str, str], object] = {}
        for sub, name, _required, _hint in all_channel_bindings():
            intent_slug = recommender.intent_for_binding(name)
            if intent_slug is None:
                continue
            pick = recommender.top_pick(intent_slug, snapshot)
            if pick is None:
                continue
            recs[(sub, name)] = plan.SetupRecommendation(
                subsystem=sub, binding_name=name, target_kind="channel",
                target_id=int(pick.channel_id),
                target_name=str(pick.channel_name),
                confidence=str(pick.confidence),
                reason=(pick.reasons[0] if pick.reasons else ""))
        return recs

    try:
        draft = await plan.suggest(int(guild_id))
    except Exception:  # noqa: BLE001 — hints simply do not appear
        logger.exception("channels: snapshot lookup raised")
        return {}
    return {(rec.subsystem, rec.binding_name): rec
            for rec in draft.recommendations}


# --- the entry embed (build_channels_embed, bytes verbatim) --------------------------------

_CHANNELS_DESCRIPTION = (
    "Bind a channel for each subsystem's declared channel slot.  "
    "Each pick stages a `bind_channel` operation in the draft — "
    "nothing applies until Final review.")

_CHANNELS_FOOTER = "Pick a binding from the select to choose a channel."


def build_channels_embed_fields(bindings, recs) -> tuple[tuple, ...]:
    """The grouped per-subsystem field list (build_channels_embed's
    body, bytes verbatim; the no-bindings field included)."""
    if not bindings:
        return ((
            "No channel bindings declared",
            "_No registered subsystem currently declares a channel "
            "binding._",
            False),)
    grouped: dict[str, list[str]] = {}
    for sub, name, required_flag, _hint in bindings:
        rec = recs.get((sub, name))
        required = " · *required*" if required_flag else ""
        if rec is not None:
            glyph = _CONFIDENCE_GLYPH.get(rec.confidence, "⬜")
            top_reason = str(getattr(rec, "reason", "") or "")
            match_str = (
                f" · {glyph} likely `#{rec.target_name}` "
                f"({rec.confidence}"
                + (f" — {top_reason}" if top_reason else "")
                + ")")
        else:
            match_str = ""
        grouped.setdefault(sub, []).append(f"`{name}`{required}{match_str}")
    return tuple(
        (sub_name, "\n".join(f"• {body}" for body in grouped[sub_name]),
         False)
        for sub_name in sorted(grouped))


# --- flow state -----------------------------------------------------------------------------

#: guild:user → the picked (subsystem, binding_name) pair.
_PICKED_BINDING: dict[str, tuple[str, str]] = {}


def _key(req_or_ctx) -> str:
    return (f"{int(req_or_ctx.guild_id or 0)}:"
            f"{int(getattr(req_or_ctx.actor, 'user_id', 0) or 0)}")


def picked_binding(ctx) -> tuple[str, str] | None:
    return _PICKED_BINDING.get(_key(ctx))


def reset_channels_state_for_tests() -> None:
    _PICKED_BINDING.clear()


# --- the recommended builder (channels._recommended_channel_ops, adapted) --------------------

async def recommended_channel_ops(guild_id: int) -> list:
    """bind_channel ops for every HIGH-confidence advisor pick on a
    live-declared channel binding (the oracle builder's semantics —
    medium/low picks are intentionally skipped)."""
    from sb.domain.setup.section_card import StagedSectionOp

    recs = await _recommendations(int(guild_id))
    declared = {(sub, name) for sub, name, _r, _h in all_channel_bindings()}
    ops: list = []
    for (sub, name), rec in sorted(recs.items()):
        if rec.confidence != "high":
            continue
        if (sub, name) not in declared:
            continue
        ops.append(StagedSectionOp(
            op_kind="bind_channel", subsystem=sub,
            payload={"subsystem": sub, "name": name, "kind": "channel",
                     "resource_id": int(rec.target_id),
                     "target_name": str(rec.target_name)},
            label_body=f"{sub}.{name} → {rec.target_name}"))
    return ops


# --- the detail panel -------------------------------------------------------------------------

def channels_detail_spec():
    """The detail picker (ChannelsSectionView + _ChannelPickView folded
    onto one panel: the binding select, the state-dependent native
    channel picker, and the wizard-origin ↩ Back to step button)."""
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        NavigationSpec, PageSpec, PanelActionSpec, PanelSpec, SelectorKind,
        SelectorSpec,
    )
    from sb.spec.refs import HandlerRef, ProviderRef

    return PanelSpec(
        panel_id=CHANNELS_DETAIL_PANEL_ID,
        subsystem="setup",
        title="📡 Channels & log routing",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="channels_binding", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.channels_binding_pick"),
                options_source=ProviderRef(_BINDING_OPTIONS_PROVIDER),
                placeholder="Pick a binding to set…"),
            SelectorSpec(
                selector_id="channels_channel", kind=SelectorKind.CHANNEL,
                on_select=HandlerRef("setup.channels_channel_pick"),
                placeholder="Pick a channel…"),
        ),
        actions=(
            PanelActionSpec(
                action_id="channels_back_step", label="↩ Back to step",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.wizard_back_to_step")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("channels_binding",), ("channels_channel",),
            ("channels_back_step",))),)),
        renderer_override=HandlerRef("setup.channels_detail_render"),
        justification=(
            "the shipped channels detail is snapshot/draft-parameterized "
            "end to end (the grouped per-subsystem binding fields with "
            "likely-match hints — channels.build_channels_embed), its "
            "channel picker exists only after a binding pick (the oracle "
            "opened it as a second ephemeral view) and carries a "
            "per-binding dynamic placeholder, and its ↩ Back to step "
            "button rides only the wizard-native path (wizard_nav."
            "render_step_detail's row-4 injection) — all outside the "
            "static grammar vocabulary; the override composes the embed "
            "and filters/patches the components (no golden pins it — the "
            "oracle source does)."),
        session_lifecycle=True,
    )


def _ensure_providers() -> None:
    from sb.spec.refs import ProviderRef, is_registered, provider

    if is_registered(ProviderRef(_BINDING_OPTIONS_PROVIDER)):
        return

    @provider(_BINDING_OPTIONS_PROVIDER)
    async def binding_options(ctx):
        """_attach_binding_select's option list, verbatim caps: the
        likely-match description when the advisor proposes a channel,
        else the declared hint."""
        recs = await _recommendations(int(ctx.guild_id or 0))
        picked = picked_binding(ctx)
        options = []
        for sub, name, _required, hint in all_channel_bindings():
            rec = recs.get((sub, name))
            description = (f"likely #{rec.target_name}"[:100]
                           if rec is not None else (hint or "")[:100])
            options.append({
                "label": f"{sub}.{name}"[:100],
                "value": f"{sub}::{name}",
                "description": description or None,
                "default": picked == (sub, name),
            })
        return tuple(options)


async def _render_channels_detail(spec, ctx):
    import dataclasses

    from sb.domain.setup import wizard_nav
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    guild_id = int(ctx.guild_id or 0)
    user_id = int(getattr(ctx.actor, "user_id", 0) or 0)
    bindings = all_channel_bindings()
    recs = await _recommendations(guild_id)
    embed = RenderedEmbed(
        title="📡 Channels & log routing",
        description=_CHANNELS_DESCRIPTION,
        fields=build_channels_embed_fields(bindings, recs),
        footer=_CHANNELS_FOOTER if bindings else "",
        style_token="blurple")

    base = await render_panel(spec, ctx)
    picked = picked_binding(ctx)
    from_wizard = wizard_nav.detail_from_wizard(guild_id, user_id)
    components = []
    for c in base.components:
        leaf = c.custom_id.removeprefix(f"{spec.panel_id}.")
        if leaf == "channels_channel":
            if picked is None:
                continue    # the picker opens after a binding pick
            sub, name = picked
            c = dataclasses.replace(
                c, placeholder=f"Pick a channel for {sub}.{name}")
        elif leaf == "channels_back_step" and not from_wizard:
            continue        # the shipped wizard-native-only injection
        components.append(c)
    return dataclasses.replace(base, embed=embed,
                               components=tuple(components))


# --- handlers ---------------------------------------------------------------------------------

async def _channel_name(guild_id: int, channel_id: int) -> str | None:
    """The picked channel's name off the advisor's channel index (the
    oracle read it off the native picker's resolved channel)."""
    from sb.domain.setup import plan

    if plan._channel_index is None:
        return None
    try:
        channels = tuple(await plan._channel_index(int(guild_id)) or ())
    except Exception:  # noqa: BLE001 — the mention fallback answers
        logger.debug("channels: channel index read failed", exc_info=True)
        return None
    for channel in channels:
        if int(channel.id) == int(channel_id):
            return str(channel.name)
    return None


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.channels_binding_pick")):
        return

    @handler("setup.open_section_channels")
    async def open_section_channels(req) -> Reply | None:
        """The hub's Channels section button — gate exactly like the
        shipped hub button, land on the section card (channels.run →
        section_card.show), record the step marker."""
        from sb.domain.setup import section_card, wizard
        from sb.domain.setup.wizard import _open

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, wizard.GATE_MSG_WIZARD)
        await _open(req, section_card.card_panel_id(SLUG))
        await section_card.mark_step_in_progress(req, SLUG)
        return None

    @handler("setup.channels_binding_pick")
    async def binding_pick(req) -> Reply | None:
        """The binding select (_attach_binding_select._on_pick): stash
        the pick; the channel picker renders on the refreshed card."""
        from sb.domain.setup.wizard import _open, _refresh_own_panel

        values = tuple(req.args.get("values", ()) or ())
        key = str(values[0]) if values else ""
        sub, _sep, name = key.partition("::")
        declared = {(s, n) for s, n, _r, _h in all_channel_bindings()}
        if not _sep or (sub, name) not in declared:
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "No channel bindings declared by any subsystem.")
        _PICKED_BINDING[_key(req)] = (sub, name)
        if not await _refresh_own_panel(req, {}):
            await _open(req, CHANNELS_DETAIL_PANEL_ID)
        return None

    @handler("setup.channels_channel_pick")
    async def channel_pick(req) -> Reply | None:
        """_ChannelPickSelect.callback → _stage_channel_binding: the
        pick stages a ``bind_channel`` op; the shipped staged/pending
        confirmation answers."""
        from sb.domain.setup import section_card, wizard
        from sb.domain.setup.section_card import StagedSectionOp

        values = tuple(req.args.get("values", ()) or ())
        if not values:
            # shipped copy, verbatim.
            return Reply(BLOCKED, "No channel picked.")
        picked = _PICKED_BINDING.get(_key(req))
        if picked is None:
            # a stale card (no binding picked this session) — the
            # entry footer's instruction answers.
            return Reply(BLOCKED,
                         "Pick a binding from the select to choose a "
                         "channel.")
        raw = str(values[0])
        if not raw.lstrip("-").isdigit():
            return Reply(BLOCKED, "No channel picked.")
        # the staging gate (module docstring: additive fence — the
        # card's stage-or-skip ladder).
        if not await section_card._gated_card(req):
            return Reply(BLOCKED, section_card.GATE_MSG_CARD)
        channel_id = int(raw)
        sub, name = picked
        guild_id = int(req.guild_id or 0)
        resolved = await _channel_name(guild_id, channel_id)
        target_name = (f"#{resolved}" if resolved
                       else f"<#{channel_id}>")
        try:
            await section_card.stage_custom(guild_id, SLUG, StagedSectionOp(
                op_kind="bind_channel", subsystem=sub,
                payload={"subsystem": sub, "name": name, "kind": "channel",
                         "resource_id": channel_id,
                         "target_name": target_name},
                label_body=f"{sub}.{name} → {target_name}"))
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception("channels: setup_draft.append failed")
            # shipped copy, verbatim.
            return Reply(BLOCKED, "Could not stage the binding — see logs.")
        await section_card.mark_step_in_progress(req, SLUG)
        try:
            pending = await wizard.staged_ops_count(guild_id)
        except Exception:  # noqa: BLE001 — the shipped count soft-fail
            logger.exception("channels: setup_draft.count failed")
            pending = 0
        from sb.domain.setup.wizard import _refresh_own_panel

        await _refresh_own_panel(req, {})
        # shipped copy, verbatim (_stage_channel_binding's confirmation).
        return Reply(SUCCESS,
                     f"✅ Staged for Final review: `{sub}.{name}` → "
                     f"{target_name}.  "
                     f"Pending operations: **{pending}**.")


# --- registration -------------------------------------------------------------------------------

def _register_panels() -> None:
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    if not is_registered(HandlerRef("setup.channels_detail_render")):
        handler("setup.channels_detail_render")(_render_channels_detail)
    if not is_registered(PanelRef(CHANNELS_DETAIL_PANEL_ID)):
        panel(CHANNELS_DETAIL_PANEL_ID)(channels_detail_spec)


def _register_section() -> None:
    from sb.domain.setup import section_card

    section_card.register_recommended_builder(SLUG, recommended_channel_ops)
    section_card.register_customize_panel(SLUG, CHANNELS_DETAIL_PANEL_ID)
    section_card.register_section_card(SLUG, detected_state=_DETECTED_STATE)


_ensure_providers()
_register()
_register_panels()
_register_section()


def ensure_channels_refs() -> None:
    _ensure_providers()
    _register()
    _register_panels()
    _register_section()

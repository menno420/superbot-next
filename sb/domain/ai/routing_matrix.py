"""The ai ROUTING-MATRIX picker (band 7, the routing-matrix follow-up
slice — D-0074) — the shipped ``views/ai/routing/matrix.py`` read-only
diagnostic on this engine (reconstructed via search_code fragments
against the oracle default branch @2c7d2de7; full-file oracle reads stay
denied and NO golden pins these clicks — the trap-24 sha caveat is
ledgered in D-0074):

* the page — the behavior chooser's "Routing matrix" button swaps the
  anchor to the shipped ``_behavior_page_embed("Behavior · routing
  matrix", "Pick a channel to dry-run the AI routing matrix.")`` page
  (chooser.py ``matrix_btn``) over the shipped ``_MatrixChannelSelect``
  (native text-channel select, "Pick a channel to preview routing
  for…") — the spec lives in :mod:`sb.domain.ai.panels`
  (``ai.behavior_matrix_picker``);
* the pick — the shipped callback order: guild guard (``❌ This
  requires a guild context.``, the matrix's own byte), then ONE dry-run
  resolve (the shipped ``nlp.resolve(ctx, dry_run=True)`` → this port's
  verbatim precedence twin :func:`sb.kernel.ai.policy.resolve_policy`)
  rendered as the shipped 🧭 card: Outcome / Effective min_level /
  Effective cooldown / Instruction profiles (ids labeled with preset
  keys via the catalog, the shipped ``svc.list_presets()`` translate) /
  Precedence trace (1000-cap ellipsis) + the ``policy_snapshot=…``
  footer. READ-ONLY end to end — no audit row, no cooldown touch, no
  mutation (the shipped "No mutations." module contract; resolve_policy
  is a pure read under dry_run).

The shipped view called ``build_routing_matrix_embed`` with only
guild/channel/user ids — ``user_level`` DEFAULTS to 5 and
``user_role_ids`` to ``()`` (matrix.py's signature defaults), so the
description renders those defaults verbatim; ported as-is, never
"improved" to the invoker's real level/roles (parity pins oracle
semantics — the preview picker is the surface that resolves as the
real user). The shipped admin gate (``interaction_check`` →
"❌ Administrator permission required.") rides this engine's tier lane
(``audience_tier="staff"`` on the selector, the D-0070/D-0071 picker
posture — the kernel deny path answers). Registered at MODULE IMPORT
(BUG A rule)."""

from __future__ import annotations

import logging

from sb.kernel.interaction.handler_kit import Reply
from sb.kernel.panels.render import RenderedEmbed
from sb.spec.outcomes import SUCCESS

logger = logging.getLogger("sb.domain.ai.routing_matrix")

__all__ = [
    "build_routing_matrix_embed",
    "ensure_routing_matrix_refs",
    "routing_matrix_pick",
]

#: the shipped guild-guard byte (matrix.py _MatrixChannelSelect.callback
#: — NOT the chooser family's "❌ Edit requires a guild context.").
_NEEDS_GUILD_MATRIX = "❌ This requires a guild context."


async def _preset_lookup() -> dict[int, str]:
    """Map preset id → key (for embed labels). Falls back to ``{}``
    if the catalog is empty / unavailable (the shipped defensive
    except — ``svc.list_presets()`` here is this port's
    :func:`sb.domain.ai.behavior_presets.list_behavior_presets`)."""
    try:
        from sb.domain.ai import behavior_presets as presets

        rows = await presets.list_behavior_presets()
        return {int(p.preset_id): p.key for p in rows}
    except Exception as exc:  # noqa: BLE001 — defensive (shipped shape)
        logger.debug("routing matrix: preset catalog unavailable (%s)", exc)
        return {}


async def build_routing_matrix_embed(
    *,
    guild_id: int,
    channel_id: int,
    user_id: int,
    user_level: int = 5,
    user_role_ids: tuple[int, ...] = (),
) -> RenderedEmbed:
    """Run the resolver in dry-run mode and render the outcome — the
    shipped embed byte-for-byte (title/description/fields/footer;
    green when allowed, red when denied)."""
    from sb.kernel.ai import policy

    ctx = policy.MessageContext(
        guild_id=guild_id,
        channel_id=channel_id,
        category_id=None,
        user_id=user_id,
        user_level=user_level,
        user_role_ids=user_role_ids,
        is_mention=False,
        is_fresh_user=False,
    )
    decision = await policy.resolve_policy(ctx, dry_run=True)
    presets = await _preset_lookup()

    fields: list[tuple[str, str, bool]] = [
        ("Outcome",
         ("✅ allowed" if decision.allowed
          else f"❌ denied · `{decision.reason_code.value}`"),
         False),
        ("Effective min_level", str(decision.effective_min_level), True),
        ("Effective cooldown", f"{decision.effective_cooldown}s", True),
    ]
    if decision.instruction_profile_ids:
        labels = []
        for pid in decision.instruction_profile_ids:
            key = presets.get(int(pid))
            labels.append(f"`{pid}`" + (f" ({key})" if key else ""))
        fields.append(("Instruction profiles", ", ".join(labels), False))
    if decision.precedence_trace:
        trace = "\n".join(f"• {line}" for line in decision.precedence_trace)
        if len(trace) > 1000:
            trace = trace[:999] + "…"
        fields.append(("Precedence trace", trace, False))
    return RenderedEmbed(
        title="🧭 AI Routing matrix (dry-run)",
        description=(
            f"channel=<#{channel_id}> · user=<@{user_id}> · "
            f"user_level={user_level} · roles={list(user_role_ids) or '—'}"),
        fields=tuple(fields),
        footer=(f"policy_snapshot=`{decision.policy_snapshot_hash or '—'}` · "
                "dry-run only · no audit / no cooldown side-effects."),
        style_token="green" if decision.allowed else "red",
    )


async def routing_matrix_pick(req) -> Reply | None:
    """_MatrixChannelSelect.callback, shipped order: guild guard → the
    dry-run resolve card (the shipped ephemeral followup renders as the
    session card page — the family's ledgered edit-in-place deviation,
    the ai.policy_preview_pick lane)."""
    from sb.domain.ai.behavior_widgets import _open_page, _picked

    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_MATRIX)
    embed = await build_routing_matrix_embed(
        guild_id=int(req.guild_id),
        channel_id=int(_picked(req) or 0),
        user_id=int(getattr(req.actor, "user_id", 0) or 0))
    await _open_page(req, "ai.card", {"_card": embed})
    return None


# --- registration — MODULE IMPORT (BUG A rule) ------------------------------------------

_HANDLERS = (
    ("ai.routing_matrix_pick", routing_matrix_pick),
)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


_register()


def ensure_routing_matrix_refs() -> None:
    _register()

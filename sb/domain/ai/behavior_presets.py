"""The shipped BEHAVIOR PRESET service twin (band 7, the behavior-preset
slice — D-0071): ``services.ai_behavior_profile_service`` on this engine.

The oracle service (reconstructed via search_code fragments — full-file
oracle reads stay denied) owned three things, all ported here:

* the in-process PRESET CATALOG — each seeded ``ai_instruction_profile``
  row's UI metadata (headline + the implied channel-mode), keyed by the
  row's ``name``; rows the catalog does not recognise surface with a
  fallback entry "rather than dropping [them], so a stale catalog never
  silently hides presets from operators" (the shipped comment);
* the reads — ``list_behavior_presets`` (every ``is_preset`` row joined
  with its catalog metadata, alphabetical — the shipped name
  ``list_presets`` is taken by the aireview store twin in this flat
  package, so the port carries the qualified name) and
  ``describe_preset`` (one row by id, None when absent or not flagged
  ``is_preset``);
* ``apply_preset`` — scope roster check (channel/category ONLY), preset
  resolution, then ONE write through the policy chokepoint: the shipped
  seam called ``ai_policy_mutation.set_channel_policy`` /
  ``set_category_policy`` with ``mode=summary.recommended_mode``,
  ``min_level=UNCHANGED``, ``cooldown_seconds=UNCHANGED``,
  ``instruction_profile_id=preset_id`` — here the SAME audited
  ``ai.set_channel_policy`` / ``ai.set_category_policy`` K7 ops the
  policy widgets run (scoped upsert + bump_generation in one
  transaction, central audit, advisory event after commit; the leg
  re-checks the preset id in-txn, §4.1 seam authority).

The typed error ladder is the shipped one: ``BehaviorPresetError`` →
``InvalidBehaviorPresetScopeError`` / ``UnknownBehaviorPresetError``
(the picker echoes ``❌ {type(exc).__name__}: {exc}``). An op-level
write failure is NOT an exception on this engine (K7 classifies leg
failures into WorkflowResults) — ``apply_preset`` returns the raw
result and the widget renders the #160-ledgered envelope copy."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from sb.domain.ai import policy_store as store
from sb.kernel.interaction.handler_kit import ctx_from_request
from sb.spec.outcomes import SUCCESS

__all__ = [
    "BehaviorPresetCatalogEntry",
    "BehaviorPresetError",
    "BehaviorPresetSummary",
    "InvalidBehaviorPresetScopeError",
    "PresetApplication",
    "UnknownBehaviorPresetError",
    "apply_preset",
    "describe_preset",
    "list_behavior_presets",
]


# --- the shipped error ladder ---------------------------------------------------------


class BehaviorPresetError(Exception):
    pass


class InvalidBehaviorPresetScopeError(BehaviorPresetError):
    pass


class UnknownBehaviorPresetError(BehaviorPresetError):
    pass


#: the shipped _SUPPORTED_SCOPES — guild baseline stays the settings/modal
#: surface ("apply_preset refuses scopes outside {'channel', 'category'}",
#: the oracle service test docstring).
_SUPPORTED_SCOPES = frozenset({"channel", "category"})


# --- the shipped catalog ---------------------------------------------------------------


@dataclass(frozen=True)
class BehaviorPresetCatalogEntry:
    """In-process metadata for a built-in preset — the DB row provides
    id/name/body, the catalog adds the UI headline and the implied
    channel-mode (the shipped mapping, verbatim)."""

    key: str
    headline: str
    recommended_mode: Literal["always_reply", "mention_only", "disabled"]


_PRESET_CATALOG: dict[str, BehaviorPresetCatalogEntry] = {
    "disabled": BehaviorPresetCatalogEntry(
        key="disabled",
        headline="No AI replies in this scope",
        recommended_mode="disabled",
    ),
    "mention_only_helper": BehaviorPresetCatalogEntry(
        key="mention_only_helper",
        headline="Concise replies when mentioned",
        recommended_mode="mention_only",
    ),
    "helpful_channel": BehaviorPresetCatalogEntry(
        key="helpful_channel",
        headline="Full natural-language behavior",
        recommended_mode="always_reply",
    ),
    "btd6_focused": BehaviorPresetCatalogEntry(
        key="btd6_focused",
        headline="BTD6 grounding prioritised",
        recommended_mode="always_reply",
    ),
    "quiet_btd6_focused": BehaviorPresetCatalogEntry(
        key="quiet_btd6_focused",
        headline="BTD6 grounding, mention-only",
        recommended_mode="mention_only",
    ),
    "staff_diagnostics": BehaviorPresetCatalogEntry(
        key="staff_diagnostics",
        headline="Operator diagnostics, mention-only",
        recommended_mode="mention_only",
    ),
    "support_triage": BehaviorPresetCatalogEntry(
        key="support_triage",
        headline="Neutral support triage",
        recommended_mode="mention_only",
    ),
}


def _fallback_entry(name: str) -> BehaviorPresetCatalogEntry:
    """A DB row the catalog does not recognise — surfaced with the shipped
    fallback entry rather than dropped."""
    return BehaviorPresetCatalogEntry(
        key=name,
        headline=f"(uncatalogued preset {name!r})",
        recommended_mode="mention_only",
    )


# --- the reads ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BehaviorPresetSummary:
    """UI-friendly summary of one preset row + its catalog metadata."""

    preset_id: int
    key: str
    headline: str
    recommended_mode: str


async def list_behavior_presets() -> list[BehaviorPresetSummary]:
    """Return every seeded preset, joined with its catalog metadata."""
    rows = await store.list_preset_profiles()
    out: list[BehaviorPresetSummary] = []
    for row in rows:
        meta = _PRESET_CATALOG.get(row["name"]) or _fallback_entry(row["name"])
        out.append(BehaviorPresetSummary(
            preset_id=int(row["id"]),
            key=row["name"],
            headline=meta.headline,
            recommended_mode=meta.recommended_mode,
        ))
    return out


async def describe_preset(preset_id: int) -> BehaviorPresetSummary | None:
    """One preset by id, or None if it does not exist / is not flagged
    ``is_preset``."""
    row = await store.get_preset_profile(int(preset_id))
    if row is None:
        return None
    meta = _PRESET_CATALOG.get(row["name"]) or _fallback_entry(row["name"])
    return BehaviorPresetSummary(
        preset_id=int(row["id"]),
        key=row["name"],
        headline=meta.headline,
        recommended_mode=meta.recommended_mode,
    )


# --- the apply seam ------------------------------------------------------------------------


@dataclass(frozen=True)
class PresetApplication:
    """Returned by :func:`apply_preset` so the UI can render confirmation
    (the shipped shape; ``result`` carries the K7 WorkflowResult so the
    widget can route a non-SUCCESS write to the envelope copy)."""

    scope: str
    target_id: int
    preset_id: int
    preset_key: str
    recommended_mode: str
    policy_mutation_id: str
    result: object


async def apply_preset(req, *, scope: str, target_id: int,
                       preset_id: int) -> PresetApplication:
    """Bind one preset to one channel/category through the policy
    chokepoint (the shipped seam order: scope roster → preset resolution
    → the scoped mutation with min_level/cooldown UNTOUCHED)."""
    if scope not in _SUPPORTED_SCOPES:
        raise InvalidBehaviorPresetScopeError(
            f"scope must be one of {sorted(_SUPPORTED_SCOPES)}, "
            f"got {scope!r}")
    summary = await describe_preset(preset_id)
    if summary is None:
        raise UnknownBehaviorPresetError(
            f"preset_id={preset_id} not found or not flagged is_preset=True")

    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    if scope == "channel":
        op_key, id_key = "ai.set_channel_policy", "channel_id"
    else:
        op_key, id_key = "ai.set_category_policy", "category_id"
    # the shipped mutation seam minted a uuid per write and carried it on
    # the advisory event (the picker ack renders it verbatim).
    mutation_id = uuid.uuid4().hex
    result = await engine.run(WorkflowRef(op_key), ctx_from_request(req, {
        id_key: int(target_id),
        "mode": summary.recommended_mode,
        "instruction_profile_id": int(summary.preset_id),
        # min_level / cooldown_seconds deliberately ABSENT → the store's
        # UNCHANGED sentinel ("Existing min_level / cooldown overrides
        # for that scope are preserved.", the shipped picker copy).
        "mutation_id": mutation_id,
    }))
    return PresetApplication(
        scope=scope,
        target_id=int(target_id),
        preset_id=int(summary.preset_id),
        preset_key=summary.key,
        recommended_mode=summary.recommended_mode,
        policy_mutation_id=mutation_id if result.outcome == SUCCESS else "",
        result=result,
    )

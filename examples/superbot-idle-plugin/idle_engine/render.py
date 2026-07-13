"""Pure render layer: engine state + theme pack -> embed-shaped payloads.

This is the seam superbot-next's plugin renders through. Every function
here is PURE presentation: plain dicts shaped like Discord embeds
(``title``, ``description``, ``color`` int, ``fields`` of
``{name, value, inline}``) — no chat-platform SDK imports, no I/O, no
wall clock (callers pass ``now`` in). Same state + same theme -> the
identical payload, byte for byte.

CORE/SKIN contract: every player-visible noun (names, flavor, emoji,
embed color) comes from the theme pack. The only literals this module
contributes are neutral scaffolding — digits, separators, arrows,
status marks, and the short generic label ``Lv``. Packs may override
that scaffolding through the OPTIONAL schema-v1 ``labels`` block
(docs/theme-schema.md § labels): an offline-return flavor template
(with the one substitution token ``{gains}``), status/shop title,
shop description, level label, and prestige progress label. Every
slot is optional — an unset slot falls back to the neutral default,
so pre-labels packs render byte-identically.

Budget enforcement (PLATFORM-LIMITS.md / docs/theme-schema.md): title
<= 256, field name <= 256, field value <= 1024, description <= 4096,
<= 25 fields. Two tiers, one validator:

- Values that embed FORMATTED NUMBERS are clamped at composition time
  with an ellipsis — a quintillion-digit balance is a display problem,
  not an error.
- THEME-SOURCED text is never truncated: the theme-gate already bounds
  it, so a slot it overflows means a broken pack or an engine bug —
  :func:`validate_embed` (run on every payload) raises
  :class:`RenderBudgetError` instead of silently mangling themed text.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from idle_engine.achievements import (
    milestone_earned,
    milestone_progress,
    milestone_reached,
)
from idle_engine.engine import offline_progress, production_per_second
from idle_engine.prestige import prestige_award, prestige_eligible
from idle_engine.upgrades import upgrade_cost

if TYPE_CHECKING:  # imported for type checking only: keeps runtime stdlib-only
    from idle_engine.state import GameState
    from idle_engine.theme import Theme

# Embed caps — the verbatim platform walls this layer guarantees.
TITLE_LIMIT = 256
FIELD_NAME_LIMIT = 256
FIELD_VALUE_LIMIT = 1024
DESCRIPTION_LIMIT = 4096
MAX_FIELDS = 25

# The shop flavor slot: the budget an upgrade's themed ``description`` gets
# inside the composed shop field value. Derived by the composition
# arithmetic (docs/theme-schema.md § budgets), which spends the 1024-char
# field-value cap exactly: description (768) + newline (1) + the cost
# line's themed fixed text (mark 1 + level label 32 + currency emoji 32 +
# currency name 64 + separators 10 = 139) + digit floor (116) = 1024.
# The machine schema's ``$defs.shop_flavor_text`` mirrors this number —
# ``tests/test_render.py`` pins the two equal so neither can drift alone.
SHOP_FLAVOR_LIMIT = 768

_ELLIPSIS = "…"
_HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}\Z")

# The one substitution token themed label templates may carry. Kept as a
# local literal (mirroring idle_engine.theme.GAINS_PLACEHOLDER) because
# this module must stay runtime-stdlib-only and never import the
# yaml-loading theme module.
_GAINS_PLACEHOLDER = "{gains}"

# Neutral scaffolding fallback for the shop level label.
_NEUTRAL_LEVEL_LABEL = "Lv"

# Neutral scaffolding fallback for an unskinned milestone slot's field
# name: "Milestone {n}" numbered by the slot's position in the engine's
# derived spec list (generic engine vocabulary, like "Lv" — never a
# theme noun).
_NEUTRAL_MILESTONE_LABEL = "Milestone"

# Neutral status glyphs — generic scaffolding, never theme nouns (like the
# ✅/🔒 marks already used across the views). ``_MILESTONE_READY_MARK`` flags a
# milestone whose live progress has reached the threshold but which the
# runtime has not yet banked via ``award_milestones`` (a "ready to claim"
# state) — distinct from 🔒 (still short of the threshold), so a reached
# milestone never renders as a past-100%-but-locked line that reads as a bug.
_MILESTONE_READY_MARK = "⏳"  # ⏳ hourglass — reached, awaiting the award action

# ``_UPGRADE_UNAVAILABLE_MARK`` / ``_REQUIRES_LABEL`` flag a shop upgrade whose
# target generator is 0-owned: purchasing it multiplies a rate of zero, so it
# spends currency for no observable effect. Display-only — purchase mechanics
# and costs are unchanged; the annotation warns rather than blocks. "requires"
# is generic engine vocabulary (like "Lv"), never a theme noun.
_UPGRADE_UNAVAILABLE_MARK = "⚠️"  # ⚠️ — target generator not yet owned
_REQUIRES_LABEL = "requires"


class RenderBudgetError(ValueError):
    """A theme-sourced string overflowed an embed budget (engine/pack bug)."""


def embed_color_int(hex_color: str) -> int:
    """Parse a theme's ``#RRGGBB`` accent color to the wire's decimal RGB."""
    if not isinstance(hex_color, str) or not _HEX_COLOR.match(hex_color):
        raise ValueError(f"embed color must be #RRGGBB hex, got {hex_color!r}")
    return int(hex_color[1:], 16)


def _format_amount(amount: int) -> str:
    """Deterministic integer formatting with thousands separators."""
    return f"{amount:,}"


def _clamp(text: str, limit: int) -> str:
    """Safe truncation WITH ellipsis, for numeric/formatted content only.

    Never applied to theme-sourced strings on their own — those raise via
    :func:`validate_embed` instead (silent truncation would hide a bug the
    gate exists to prevent).
    """
    if len(text) <= limit:
        return text
    if limit < len(_ELLIPSIS):
        return ""
    return text[: limit - len(_ELLIPSIS)] + _ELLIPSIS


def validate_embed(embed: dict) -> dict:
    """The single budget gate: every view returns through here.

    Raises :class:`RenderBudgetError` on any cap violation. Because all
    number-bearing strings were already clamped at composition time, a
    failure here means theme-sourced text overflowed a slot the gate
    bounds it to fit — an engine or pack bug, surfaced loudly.
    """
    checks = [
        (1 <= len(embed["title"]) <= TITLE_LIMIT, "title", len(embed["title"])),
        (
            len(embed["description"]) <= DESCRIPTION_LIMIT,
            "description",
            len(embed["description"]),
        ),
        (len(embed["fields"]) <= MAX_FIELDS, "fields", len(embed["fields"])),
        (0 <= embed["color"] <= 0xFFFFFF, "color", embed["color"]),
    ]
    for i, field in enumerate(embed["fields"]):
        checks.append(
            (1 <= len(field["name"]) <= FIELD_NAME_LIMIT, f"fields[{i}].name", len(field["name"]))
        )
        checks.append(
            (
                1 <= len(field["value"]) <= FIELD_VALUE_LIMIT,
                f"fields[{i}].value",
                len(field["value"]),
            )
        )
    for ok, slot, measured in checks:
        if not ok:
            raise RenderBudgetError(
                f"embed budget violated at {slot!r} (measured {measured}): "
                "theme-sourced text overflowed a gate-bounded slot"
            )
    return embed


def _field(name: str, value: str, inline: bool) -> dict:
    return {"name": name, "value": value, "inline": inline}


def _labelled(emoji: str, name: str) -> str:
    """The one composition rule for themed labels: ``{emoji} {name}``."""
    return f"{emoji} {name}"


def _prestige_specs(theme: Theme) -> list:
    spec = theme.prestige_spec()
    return [spec] if spec is not None else []


def _label_slot(theme: Theme, slot: str) -> str | None:
    """The pack's themed override for a render label, or ``None``.

    Reads the OPTIONAL ``labels`` block (schema v1, additive): an absent
    block, or an unset/empty slot, yields ``None`` so the caller falls
    back to the neutral scaffolding this layer shipped with.
    """
    labels = theme.labels
    if labels is None:
        return None
    return getattr(labels, slot, None) or None


def render_status(state: GameState, theme: Theme, now: int) -> dict:
    """The status view: balances, generator counts + rates, offline gains.

    ``now`` is the caller's unix timestamp; production accrued since
    ``state.last_seen`` is DISPLAYED (never credited — crediting is
    :func:`idle_engine.engine.apply_offline_progress`, the engine's job).
    """
    specs = theme.generator_specs()
    upgrade_specs = theme.upgrade_specs()
    prestige_specs = _prestige_specs(theme)
    milestone_specs = theme.milestone_specs()
    rates = production_per_second(
        state, specs, upgrade_specs, prestige_specs, milestone_specs
    )
    earned = offline_progress(
        state, specs, state.last_seen, now, upgrade_specs, prestige_specs, milestone_specs
    )

    description = theme.description
    gain_lines = []
    for currency in theme.currencies.values():
        amount = earned.get(currency.currency_id, 0)
        if amount > 0:
            gain_lines.append(
                f"+{_format_amount(amount)} {_labelled(currency.emoji, currency.name)}"
            )
    if gain_lines:
        gains_text = "\n".join(gain_lines)
        template = _label_slot(theme, "offline_return")
        if template is not None:
            # Themed flavor line: replace the one substitution token with
            # the formatted gains, clamped (numeric tier) to the room the
            # fixed template text leaves. The template itself is
            # theme-sourced — never truncated; if it cannot fit,
            # validate_embed raises (theme-overflow tier).
            fixed = len(template) - len(_GAINS_PLACEHOLDER)
            room = DESCRIPTION_LIMIT - len(description) - 2 - fixed
            line = template.replace(_GAINS_PLACEHOLDER, _clamp(gains_text, max(room, 0)), 1)
            description = description + "\n\n" + line
        else:
            room = DESCRIPTION_LIMIT - len(description) - 2
            if room >= 1:
                description = description + "\n\n" + _clamp(gains_text, room)

    fields = []
    prestige_currency = theme.prestige.currency if theme.prestige else None
    for currency in theme.currencies.values():
        cid = currency.currency_id
        if cid == prestige_currency:
            held = state.prestige.get(cid, 0)
            value = _format_amount(held)
        else:
            value = _format_amount(state.balances.get(cid, 0))
            rate = rates.get(cid, 0)
            if rate > 0:
                value += f" (+{_format_amount(rate)}/s)"
        fields.append(
            _field(_labelled(currency.emoji, currency.name), _clamp(value, FIELD_VALUE_LIMIT), True)
        )
    for generator in theme.generators.values():
        spec = next(s for s in specs if s.spec_id == generator.generator_id)
        count = state.owned.get(spec.spec_id, 0)
        value = f"× {_format_amount(count)}"
        if count:
            rate = production_per_second(
                state, [spec], upgrade_specs, prestige_specs, milestone_specs
            ).get(spec.produces, 0)
            value += f" · +{_format_amount(rate)}/s"
        fields.append(
            _field(_labelled(generator.emoji, generator.name), _clamp(value, FIELD_VALUE_LIMIT), True)
        )

    return validate_embed(
        {
            "title": _label_slot(theme, "status_title") or _labelled(theme.emoji, theme.name),
            "description": description,
            "color": embed_color_int(theme.embed_color),
            "fields": fields,
        }
    )


def render_shop(state: GameState, theme: Theme) -> dict | None:
    """The upgrade-shop view: cost line + themed flavor per upgrade.

    Returns ``None`` when the pack declares no ``upgrades`` block. Costs
    come from the engine's pre-registered curve (``idle_engine.economy``)
    at the state's CURRENT level. Each field value composes the
    number-bearing cost line (mark, level, cost — numeric tier: clamps)
    and, on the line below, the upgrade's themed flavor ``description``
    (theme-sourced tier: never truncated; overflowing its
    :data:`SHOP_FLAVOR_LIMIT` slot raises :class:`RenderBudgetError`).
    The cost line clamps into exactly the room the description leaves,
    so a gate-legal pack can never bust the 1024-char field-value cap
    (arithmetic at :data:`SHOP_FLAVOR_LIMIT`). An upgrade without a
    description renders the bare cost line byte-identically to the
    pre-composition layer.
    """
    if not theme.upgrades:
        return None
    spec_by_id = {spec.spec_id: spec for spec in theme.upgrade_specs()}
    level_label = _label_slot(theme, "level") or _NEUTRAL_LEVEL_LABEL
    fields = []
    for upgrade in theme.upgrades.values():
        spec = spec_by_id[upgrade.upgrade_id]
        level = state.upgrades.get(spec.spec_id, 0)
        cost = upgrade_cost(spec, level)
        affordable = state.balances.get(spec.cost_currency, 0) >= cost
        currency = theme.currencies[spec.cost_currency]
        target_owned = state.owned.get(spec.target, 0)
        if target_owned == 0:
            # Trap-buy guard (display only): this upgrade multiplies the rate
            # of a generator the player owns ZERO of, so a purchase spends
            # currency for no observable effect. Mark it unavailable and name
            # the generator it needs, instead of an affordable ✅ that invites
            # a wasted buy. Purchase logic and costs are UNCHANGED — the
            # annotation warns, it does not block.
            mark = _UPGRADE_UNAVAILABLE_MARK
            target = theme.generators.get(spec.target)
            requires = (
                _labelled(target.emoji, target.name) if target is not None else spec.target
            )
            suffix = f" · {_REQUIRES_LABEL} {requires}"
        else:
            mark = "✅" if affordable else "\U0001f512"
            suffix = ""
        cost_line = (
            f"{mark} {level_label} {_format_amount(level)} → {_format_amount(level + 1)}"
            f" · {_format_amount(cost)} {_labelled(currency.emoji, currency.name)}"
            f"{suffix}"
        )
        description = upgrade.description or ""
        if len(description) > SHOP_FLAVOR_LIMIT:
            # Theme-sourced overflow tier: the gate bounds this slot, so an
            # overflow is a broken pack or an engine bug — raise instead of
            # letting the numeric clamp silently starve the cost line.
            raise RenderBudgetError(
                f"embed budget violated at 'upgrade.description' (measured "
                f"{len(description)}, slot {SHOP_FLAVOR_LIMIT}): theme-sourced "
                "text overflowed a gate-bounded slot"
            )
        if description:
            room = FIELD_VALUE_LIMIT - len(description) - 1
            value = f"{_clamp(cost_line, room)}\n{description}"
        else:
            value = _clamp(cost_line, FIELD_VALUE_LIMIT)
        fields.append(_field(_labelled(upgrade.emoji, upgrade.name), value, False))
    return validate_embed(
        {
            "title": _label_slot(theme, "shop_title") or _labelled(theme.emoji, theme.name),
            "description": _label_slot(theme, "shop_description") or theme.description,
            "color": embed_color_int(theme.embed_color),
            "fields": fields,
        }
    )


def render_prestige(state: GameState, theme: Theme) -> dict | None:
    """The prestige view: eligibility, progress, projected award.

    Returns ``None`` when the pack declares no ``prestige`` block. Shows
    (never performs) the reset: progress of the measured currency toward
    the threshold, and the held prestige balance with the award a reset
    right now would bank.
    """
    if theme.prestige is None:
        return None
    spec = theme.prestige_spec()
    measured = theme.currencies[theme.prestige.measures]
    awarded = theme.currencies[theme.prestige.currency]
    lifetime = state.lifetime.get(spec.measures, 0)
    held = state.prestige.get(spec.awards, 0)
    mark = "✅" if prestige_eligible(state, spec) else "\U0001f512"
    progress_label = _label_slot(theme, "prestige_progress")
    progress_prefix = f"{mark} {progress_label}" if progress_label else mark
    progress = f"{progress_prefix} {_format_amount(lifetime)} / {_format_amount(spec.threshold)}"
    projected = f"{_format_amount(held)} (+{_format_amount(prestige_award(state, spec))})"
    fields = [
        _field(_labelled(measured.emoji, measured.name), _clamp(progress, FIELD_VALUE_LIMIT), True),
        _field(_labelled(awarded.emoji, awarded.name), _clamp(projected, FIELD_VALUE_LIMIT), True),
    ]
    return validate_embed(
        {
            "title": _labelled(theme.prestige.action_emoji, theme.prestige.action_name),
            "description": theme.prestige.action_description,
            "color": embed_color_int(theme.embed_color),
            "fields": fields,
        }
    )


def render_achievements(state: GameState, theme: Theme) -> dict:
    """The achievements view: one field per engine-derived milestone slot.

    The slot SET is mechanics (identical pre-registered ladders for
    every pack — ``idle_engine.economy``), so this view always renders:
    at most 9 slots, its OWN embed, far under the 25-field cap (the
    status view already spends up to 25 fields on currencies +
    generators, which is why milestones do not ride there). The pack's
    OPTIONAL ``milestones`` block skins individual slots; an unskinned
    slot falls back to neutral scaffolding (``Milestone {n}``, the bare
    progress numbers) so a pack without the block renders byte-stable
    neutral output.

    Field value composition mirrors the shop's two tiers: the progress
    line (mark + numbers) is number-bearing and CLAMPS; the themed
    flavor ``description`` below it is theme-sourced — never truncated;
    overflowing its :data:`SHOP_FLAVOR_LIMIT` slot raises
    :class:`RenderBudgetError`. An EARNED milestone pins its numbers at
    ``threshold / threshold`` (the counters it watched may since have
    reset — e.g. a prestige wiped ``owned`` — but an earn is forever);
    an unearned one shows live progress, mark strictly reflecting the
    earned set (awarding is the runtime's explicit action).
    """
    fields = []
    for position, spec in enumerate(theme.milestone_specs(), 1):
        if milestone_earned(state, spec):
            mark = "✅"
            progress = spec.threshold
        elif milestone_reached(state, spec):
            # Reached the threshold, but awarding is the runtime's explicit
            # action (award_milestones) and has not run yet. Show a distinct
            # "ready" glyph and CAP the numerator at the threshold, so this
            # never renders as "5,000 / 1,000 🔒" (past 100% but locked, which
            # reads as a bug). Display-only: the earned SET is unchanged.
            mark = _MILESTONE_READY_MARK
            progress = spec.threshold
        else:
            mark = "\U0001f512"
            progress = milestone_progress(state, spec)
        line = f"{mark} {_format_amount(progress)} / {_format_amount(spec.threshold)}"
        themed = theme.milestones.get(spec.spec_id)
        if themed is not None:
            name = _labelled(themed.emoji, themed.name)
            description = themed.description or ""
            if len(description) > SHOP_FLAVOR_LIMIT:
                # Theme-sourced overflow tier: the gate bounds this slot, so
                # an overflow is a broken pack or an engine bug — raise
                # instead of letting the numeric clamp starve the line.
                raise RenderBudgetError(
                    f"embed budget violated at 'milestone.description' (measured "
                    f"{len(description)}, slot {SHOP_FLAVOR_LIMIT}): theme-sourced "
                    "text overflowed a gate-bounded slot"
                )
        else:
            name = f"{_NEUTRAL_MILESTONE_LABEL} {position}"
            description = ""
        if description:
            room = FIELD_VALUE_LIMIT - len(description) - 1
            value = f"{_clamp(line, room)}\n{description}"
        else:
            value = _clamp(line, FIELD_VALUE_LIMIT)
        fields.append(_field(name, value, True))
    return validate_embed(
        {
            "title": _labelled(theme.emoji, theme.name),
            "description": theme.description,
            "color": embed_color_int(theme.embed_color),
            "fields": fields,
        }
    )

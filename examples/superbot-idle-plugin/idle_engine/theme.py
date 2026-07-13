"""Theme loading — the SKIN side of the CORE/SKIN split.

A theme pack is a data-only YAML file. It supplies every player-visible
noun: theme name, currency names, generator names, upgrade names, the
prestige currency's and prestige action's names, flavor text, emoji,
and embed color. This module maps those nouns onto opaque engine ids;
nothing in this package hard-codes any theme vocabulary. Economy
numbers (cost curves, effects, thresholds) never ride in the pack —
they come from :mod:`idle_engine.economy` (pre-registered, CORE side).
The ONE bounded exception the founding contract allows: an optional
``balance`` block carrying per-generator ``rate_multiplier_pct``
values, hard-bounded to the schema-declared 90..110 range (see
:data:`RATE_MULTIPLIER_MIN` / :data:`RATE_MULTIPLIER_MAX` below).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

from idle_engine import economy
from idle_engine.achievements import MilestoneSpec
from idle_engine.prestige import PrestigeSpec
from idle_engine.state import GeneratorSpec
from idle_engine.upgrades import UpgradeSpec


@dataclass(frozen=True)
class ThemeCurrency:
    currency_id: str
    name: str
    description: str
    emoji: str


# The theme lane's ONE bounded balance knob (founding contract: "Balance
# multipliers only within schema-declared bounds"). The same 90..110
# bounds live in schema/theme.schema.json as min/max — parity is
# test-pinned — and are validated HERE independently of the gate
# (defense in depth: an out-of-bounds pack raises even if it somehow
# bypassed CI). 100 = neutral; an absent block/entry means 100. The
# range is flavor-level variance only, never progression-defining;
# shipping a non-neutral value is a sim-gated tuning decision (Q-0264,
# docs/design/theme-balance-v0.md).
RATE_MULTIPLIER_MIN = 90
RATE_MULTIPLIER_NEUTRAL = 100
RATE_MULTIPLIER_MAX = 110


@dataclass(frozen=True)
class ThemeGenerator:
    generator_id: str
    name: str
    description: str
    emoji: str
    produces: str
    base_rate: int
    rate_multiplier_pct: int = RATE_MULTIPLIER_NEUTRAL


@dataclass(frozen=True)
class ThemeUpgrade:
    upgrade_id: str
    name: str
    description: str
    emoji: str
    target: str


# The one substitution token themed label templates may carry. The render
# layer replaces it verbatim (idle_engine/render.py keeps its own copy of
# this literal: it must not import this yaml-loading module at runtime).
GAINS_PLACEHOLDER = "{gains}"

_LABEL_SLOTS = (
    "offline_return",
    "status_title",
    "shop_title",
    "shop_description",
    "level",
    "prestige_progress",
)


@dataclass(frozen=True)
class ThemeLabels:
    """Optional themed overrides for render labels — every slot optional.

    An unset (``None``) slot falls back to the render layer's neutral
    scaffolding, so a pack without a ``labels`` block renders exactly as
    it did before the block existed.
    """

    offline_return: str | None = None
    status_title: str | None = None
    shop_title: str | None = None
    shop_description: str | None = None
    level: str | None = None
    prestige_progress: str | None = None


@dataclass(frozen=True)
class ThemePrestige:
    currency: str
    measures: str
    action_name: str
    action_description: str
    action_emoji: str


@dataclass(frozen=True)
class ThemeMilestone:
    """Nouns for one engine-derived milestone slot — SKIN only.

    ``milestone_id`` names the canonical slot (``owned-1`` …
    ``prestige-3``); thresholds and bonuses live engine-side
    (:mod:`idle_engine.economy`, pre-registered). An unskinned slot
    still exists mechanically and renders as neutral scaffolding.
    """

    milestone_id: str
    name: str
    description: str
    emoji: str


@dataclass(frozen=True)
class Theme:
    theme_id: str
    name: str
    description: str
    emoji: str
    embed_color: str
    currencies: dict[str, ThemeCurrency]
    generators: dict[str, ThemeGenerator]
    upgrades: dict[str, ThemeUpgrade] = field(default_factory=dict)
    prestige: ThemePrestige | None = None
    labels: ThemeLabels | None = None
    milestones: dict[str, ThemeMilestone] = field(default_factory=dict)

    def currency_name(self, currency_id: str) -> str:
        return self.currencies[currency_id].name

    def generator_name(self, generator_id: str) -> str:
        return self.generators[generator_id].name

    def upgrade_name(self, upgrade_id: str) -> str:
        return self.upgrades[upgrade_id].name

    def generator_specs(self) -> list[GeneratorSpec]:
        """Mechanical specs for the engine, stripped of all display data.

        ``rate_multiplier_pct`` rides along: it is the one BALANCE datum
        a pack may carry, and only within the schema-declared bounds the
        loader has already enforced.
        """
        return [
            GeneratorSpec(
                spec_id=g.generator_id,
                produces=g.produces,
                base_rate=g.base_rate,
                rate_multiplier_pct=g.rate_multiplier_pct,
            )
            for g in self.generators.values()
        ]

    def upgrade_specs(self) -> list[UpgradeSpec]:
        """Engine upgrade specs: theme names the slot, economy prices it."""
        by_id = {g.generator_id: g for g in self.generators.values()}
        return [
            economy.build_upgrade_spec(
                u.upgrade_id,
                GeneratorSpec(
                    spec_id=u.target,
                    produces=by_id[u.target].produces,
                    base_rate=by_id[u.target].base_rate,
                ),
            )
            for u in self.upgrades.values()
        ]

    def prestige_spec(self) -> PrestigeSpec | None:
        """Engine prestige spec, or None when the pack declares no track."""
        if self.prestige is None:
            return None
        return economy.build_prestige_spec(
            awards=self.prestige.currency, measures=self.prestige.measures
        )

    def milestone_specs(self) -> list[MilestoneSpec]:
        """The engine-derived milestone slots for this pack's roster.

        The slot SET is mechanics (identical ladders for every pack —
        CORE side); the pack's ``milestones`` block only skins slot ids
        with nouns. The lifetime track measures the prestige track's
        measured currency when one is declared, else — deterministic
        fallback — the FIRST declared generator's produced currency;
        the prestige track's slots exist only alongside a prestige
        block.
        """
        if self.prestige is not None:
            lifetime_currency = self.prestige.measures
            prestige_currency = self.prestige.currency
        else:
            lifetime_currency = next(iter(self.generators.values())).produces
            prestige_currency = None
        return economy.build_milestone_specs(lifetime_currency, prestige_currency)


def _require_str(mapping: dict, key: str, where: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: field {key!r} must be a non-empty string")
    return value


def load_theme(path: str | Path) -> Theme:
    """Load and structurally validate a theme pack from YAML."""
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: theme pack must be a mapping")

    meta = data.get("theme")
    if not isinstance(meta, dict):
        raise ValueError(f"{path}: missing 'theme' mapping")
    where = f"{path}:theme"
    theme_id = _require_str(meta, "id", where)
    name = _require_str(meta, "name", where)
    description = _require_str(meta, "description", where)
    emoji = _require_str(meta, "emoji", where)
    embed_color = _require_str(meta, "embed_color", where)

    raw_currencies = data.get("currencies")
    if not isinstance(raw_currencies, list) or not raw_currencies:
        raise ValueError(f"{path}: 'currencies' must be a non-empty list")
    currencies: dict[str, ThemeCurrency] = {}
    for i, entry in enumerate(raw_currencies):
        if not isinstance(entry, dict):
            raise ValueError(f"{path}:currencies[{i}] must be a mapping")
        w = f"{path}:currencies[{i}]"
        cid = _require_str(entry, "id", w)
        currencies[cid] = ThemeCurrency(
            currency_id=cid,
            name=_require_str(entry, "name", w),
            description=_require_str(entry, "description", w),
            emoji=_require_str(entry, "emoji", w),
        )

    raw_generators = data.get("generators")
    if not isinstance(raw_generators, list) or not raw_generators:
        raise ValueError(f"{path}: 'generators' must be a non-empty list")
    generators: dict[str, ThemeGenerator] = {}
    for i, entry in enumerate(raw_generators):
        if not isinstance(entry, dict):
            raise ValueError(f"{path}:generators[{i}] must be a mapping")
        w = f"{path}:generators[{i}]"
        gid = _require_str(entry, "id", w)
        produces = _require_str(entry, "produces", w)
        if produces not in currencies:
            raise ValueError(f"{w}: 'produces' ({produces!r}) is not a declared currency id")
        base_rate = entry.get("base_rate")
        if not isinstance(base_rate, int) or isinstance(base_rate, bool) or base_rate < 1:
            raise ValueError(f"{w}: 'base_rate' must be a positive integer")
        generators[gid] = ThemeGenerator(
            generator_id=gid,
            name=_require_str(entry, "name", w),
            description=_require_str(entry, "description", w),
            emoji=_require_str(entry, "emoji", w),
            produces=produces,
            base_rate=base_rate,
        )

    raw_balance = data.get("balance")
    if raw_balance is not None:
        if not isinstance(raw_balance, list) or not raw_balance:
            raise ValueError(f"{path}: 'balance', when present, must be a non-empty list")
        seen: set[str] = set()
        for i, entry in enumerate(raw_balance):
            if not isinstance(entry, dict):
                raise ValueError(f"{path}:balance[{i}] must be a mapping")
            w = f"{path}:balance[{i}]"
            gid = _require_str(entry, "generator", w)
            if gid not in generators:
                raise ValueError(
                    f"{w}: 'generator' ({gid!r}) is not a declared generator id"
                )
            if gid in seen:
                raise ValueError(f"{w}: duplicate balance entry for generator {gid!r}")
            seen.add(gid)
            pct = entry.get("rate_multiplier_pct")
            if not isinstance(pct, int) or isinstance(pct, bool):
                raise ValueError(
                    f"{w}: 'rate_multiplier_pct' must be an integer percent"
                )
            # Defense in depth: the SAME schema-declared bounds the gate
            # enforces, re-checked at load time — an out-of-bounds pack
            # raises here even if it never met the gate.
            if not RATE_MULTIPLIER_MIN <= pct <= RATE_MULTIPLIER_MAX:
                raise ValueError(
                    f"{w}: 'rate_multiplier_pct' ({pct}) is outside the "
                    f"schema-declared bounds "
                    f"{RATE_MULTIPLIER_MIN}..{RATE_MULTIPLIER_MAX}"
                )
            generators[gid] = replace(generators[gid], rate_multiplier_pct=pct)

    upgrades: dict[str, ThemeUpgrade] = {}
    raw_upgrades = data.get("upgrades")
    if raw_upgrades is not None:
        if not isinstance(raw_upgrades, list) or not raw_upgrades:
            raise ValueError(f"{path}: 'upgrades', when present, must be a non-empty list")
        for i, entry in enumerate(raw_upgrades):
            if not isinstance(entry, dict):
                raise ValueError(f"{path}:upgrades[{i}] must be a mapping")
            w = f"{path}:upgrades[{i}]"
            uid = _require_str(entry, "id", w)
            if uid in upgrades:
                raise ValueError(f"{w}: duplicate upgrade id {uid!r}")
            target = _require_str(entry, "target", w)
            if target not in generators:
                raise ValueError(
                    f"{w}: 'target' ({target!r}) is not a declared generator id"
                )
            upgrades[uid] = ThemeUpgrade(
                upgrade_id=uid,
                name=_require_str(entry, "name", w),
                description=_require_str(entry, "description", w),
                emoji=_require_str(entry, "emoji", w),
                target=target,
            )

    prestige: ThemePrestige | None = None
    raw_prestige = data.get("prestige")
    if raw_prestige is not None:
        if not isinstance(raw_prestige, dict):
            raise ValueError(f"{path}: 'prestige', when present, must be a mapping")
        w = f"{path}:prestige"
        currency = _require_str(raw_prestige, "currency", w)
        measures = _require_str(raw_prestige, "measures", w)
        for label, cid in (("currency", currency), ("measures", measures)):
            if cid not in currencies:
                raise ValueError(
                    f"{w}: {label!r} ({cid!r}) is not a declared currency id"
                )
        if currency == measures:
            raise ValueError(
                f"{w}: 'currency' and 'measures' must differ (a track cannot "
                f"measure the currency it awards)"
            )
        prestige = ThemePrestige(
            currency=currency,
            measures=measures,
            action_name=_require_str(raw_prestige, "action_name", w),
            action_description=_require_str(raw_prestige, "action_description", w),
            action_emoji=_require_str(raw_prestige, "action_emoji", w),
        )

    labels: ThemeLabels | None = None
    raw_labels = data.get("labels")
    if raw_labels is not None:
        if not isinstance(raw_labels, dict) or not raw_labels:
            raise ValueError(f"{path}: 'labels', when present, must be a non-empty mapping")
        w = f"{path}:labels"
        for key in raw_labels:
            if key not in _LABEL_SLOTS:
                raise ValueError(f"{w}: unknown label slot {key!r}")
        values = {key: _require_str(raw_labels, key, w) for key in raw_labels}
        template = values.get("offline_return")
        if template is not None:
            if template.count(GAINS_PLACEHOLDER) != 1:
                raise ValueError(
                    f"{w}.offline_return: must contain the substitution token "
                    f"{GAINS_PLACEHOLDER!r} exactly once"
                )
            remainder = template.replace(GAINS_PLACEHOLDER, "")
            if "{" in remainder or "}" in remainder:
                raise ValueError(
                    f"{w}.offline_return: unknown placeholder or stray brace — the "
                    f"only substitution token is {GAINS_PLACEHOLDER!r}"
                )
        labels = ThemeLabels(**values)

    milestones: dict[str, ThemeMilestone] = {}
    raw_milestones = data.get("milestones")
    if raw_milestones is not None:
        if not isinstance(raw_milestones, list) or not raw_milestones:
            raise ValueError(
                f"{path}: 'milestones', when present, must be a non-empty list"
            )
        # The slot set is ENGINE-derived (economy ladders); nouns may only
        # skin slots that exist for this pack's roster.
        first_produces = next(iter(generators.values())).produces
        slot_ids = {
            spec.spec_id
            for spec in economy.build_milestone_specs(
                prestige.measures if prestige else first_produces,
                prestige.currency if prestige else None,
            )
        }
        for i, entry in enumerate(raw_milestones):
            if not isinstance(entry, dict):
                raise ValueError(f"{path}:milestones[{i}] must be a mapping")
            w = f"{path}:milestones[{i}]"
            mid = _require_str(entry, "id", w)
            if mid not in slot_ids:
                raise ValueError(
                    f"{w}: id {mid!r} is not an engine milestone slot for this "
                    f"pack (valid: {sorted(slot_ids)})"
                )
            if mid in milestones:
                raise ValueError(f"{w}: duplicate milestone id {mid!r}")
            milestones[mid] = ThemeMilestone(
                milestone_id=mid,
                name=_require_str(entry, "name", w),
                description=_require_str(entry, "description", w),
                emoji=_require_str(entry, "emoji", w),
            )

    return Theme(
        theme_id=theme_id,
        name=name,
        description=description,
        emoji=emoji,
        embed_color=embed_color,
        currencies=currencies,
        generators=generators,
        upgrades=upgrades,
        prestige=prestige,
        labels=labels,
        milestones=milestones,
    )

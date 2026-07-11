"""BTD6 → AI grounding context (band 7) — the focused port of shipped
``services/btd6_context_service.py`` @7f7628e1 ``build()`` (5,622 lines):
the deterministic, dataset-backed passes that ground the QA-accuracy
corpus and the everyday tower/hero/bloon/boss/paragon question families.

Passes carried (each isolated so one failure cannot suppress the others,
shipped discipline):

1. resolver (sync, no DB) — towers/heroes/bloons/bosses/rounds (the
   resolver also matches maps/modes; in the oracle those feed only the
   ``btd6_facts`` DB pass — a D-0046 successor — so no fixture facts
   render for them here, matching shipped);
2. fixture facts — tower identity/cost/upgrades/paragon + all-difficulty
   pricing, hero identity, bloon immunity/properties/description;
3. paragon-name / paragon-degree facts (BUG-0015 "d67" disambiguation);
4. catalog facts — bosses (Standard vs ELITE per-tier health, BUG-0002),
   powers, Monkey Knowledge (MK gated on a knowledge/mk cue), rounds;
5. damage-type / status-effect INTERACTION facts (the "Lead resists
   glue" class);
6. coverage note (dataset-only source label).

NAMED SUCCESSOR PORTS (D-0046): the ``btd6_facts`` DB pass + live NK
event rows/restrictions/freshness, CT relic/tile grounding, upgrade
detail + path/parent-tower grounding, minion/sub-tower and crosspath
pricing passes, and conversation-carryover facts (needs the K10 history
scanner armed at the composition root)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sb.domain.btd6 import (
    dataset,
    difficulty_costs,
    interactions,
    keywords,
    paragon_degrees,
    resolver,
    stats,
)
from sb.kernel.ai.grounding.format import DEFAULT_CAP as _FACT_TEXT_CAP
from sb.kernel.ai.grounding.format import sanitise as _sanitise_helper

logger = logging.getLogger("sb.domain.btd6.context")

__all__ = ["BTD6Context", "build", "no_data_refusal"]

_DATASET_SOURCE_SUMMARY = "local BTD6 dataset (game data + curated)"
_FALLBACK_SOURCE_SUMMARY = "no btd6_facts rows for intent"


@dataclass(frozen=True)
class BTD6Context:
    """Retrieved facts ready for the instruction stack (shipped shape)."""

    facts: tuple[str, ...]
    source_summary: str = _FALLBACK_SOURCE_SUMMARY
    confidence: float = 0.0


def _sanitise(value: object) -> str:
    return _sanitise_helper(value, cap=_FACT_TEXT_CAP)


def _cap(line: str) -> str:
    if len(line) > _FACT_TEXT_CAP:
        return line[: _FACT_TEXT_CAP - 1] + "…"
    return line


def _dataset_label() -> str:
    return f"BTD6 game data {dataset.game_version()}"


def no_data_refusal() -> str:
    """Deterministic, version-stamped BTD6 refusal — never model prose
    (shipped ``_btd6_no_data_refusal`` verbatim)."""
    return (
        "I don't have verified BTD6 data to answer that for the current game "
        f"version ({dataset.game_version()}). I won't state names or numbers I "
        "can't ground in my data — try asking about a specific tower, hero, or "
        "paragon."
    )


# --- pass 2: fixture facts ---------------------------------------------------------


def _render_tower(entry: dataset.TowerEntry) -> list[str]:
    canonical = _sanitise(entry.canonical or entry.id)
    lines: list[str] = []
    meta_bits = []
    if entry.base_cost:
        meta_bits.append(f"base cost: {entry.base_cost} (medium difficulty)")
    if entry.category:
        meta_bits.append(f"category: {_sanitise(entry.category)}")
    meta = " | ".join(meta_bits)
    lines.append(
        _cap(
            f"[btd6_tower] {canonical} — {meta} (source: {_dataset_label()})"
            if meta
            else f"[btd6_tower] {canonical} (source: {_dataset_label()})",
        ),
    )
    for path_name, upgrades in entry.upgrade_paths.items():
        if not upgrades:
            continue
        costs = entry.upgrade_costs.get(path_name, ())
        if costs and any(costs):
            parts = [
                f"{u} (${c})" if c else u
                for u, c in zip(upgrades, costs, strict=False)
            ]
            upgrades_str = ", ".join(parts)
        else:
            upgrades_str = ", ".join(u for u in upgrades if u)
        lines.append(
            _cap(
                f"[btd6_tower] {canonical} {path_name} upgrades: "
                f"{upgrades_str} (source: {_dataset_label()})",
            ),
        )
    if entry.description:
        lines.append(
            _cap(
                f"[btd6_tower] {canonical} — {_sanitise(entry.description)} "
                f"(source: {_dataset_label()})",
            ),
        )
    lines.extend(_render_paragon_identity(entry.id, canonical))
    lines.extend(_render_tower_costs(entry, canonical))
    return lines


def _render_paragon_identity(tower_id: str, canonical: str) -> list[str]:
    """One line naming this tower's Paragon (tier 6) + Medium cost —
    shipped ``_render_paragon`` (the absence-guard's affirm source)."""
    line = stats.get_tower_paragon_line(tower_id)
    if line is None:
        return []
    name, cost = line
    name = name or f"{canonical} Paragon"
    return [
        _cap(
            f"[btd6_paragon] {canonical}'s Paragon (tier 6) is {name}, costing "
            f"{cost} on Medium (source: bloonswiki)",
        ),
    ]


def _render_tower_costs(entry: dataset.TowerEntry, canonical: str) -> list[str]:
    """All-difficulty base + per-path cumulative pricing lines (shipped
    ``_render_tower_costs`` semantics over the committed multipliers)."""
    if not entry.base_cost:
        return []
    diffs = difficulty_costs.DIFFICULTIES
    base = {d: difficulty_costs.cost_for_difficulty(entry.base_cost, d) for d in diffs}
    lines = [
        _cap(
            f"[btd6_cost] {canonical} pricing — Medium from {_dataset_label()}; "
            "Easy/Hard/Impoppable = Medium ×0.85/1.08/1.20 rounded to $5; "
            "'to reach' = tower base + all earlier tiers on that path.",
        ),
        _cap(
            f"[btd6_cost] {canonical} base placement: Easy ${base['easy']:,}, "
            f"Medium ${base['medium']:,}, Hard ${base['hard']:,}, "
            f"Impoppable ${base['impoppable']:,}",
        ),
    ]
    for pkey, tier_costs in entry.upgrade_costs.items():
        names = entry.upgrade_paths.get(pkey, ())
        cumulative = {d: base[d] for d in diffs}
        for tier, medium_cost in enumerate(tier_costs, start=1):
            per = {
                d: difficulty_costs.cost_for_difficulty(medium_cost, d) for d in diffs
            }
            for d in diffs:
                cumulative[d] += per[d]
            name = names[tier - 1] if tier - 1 < len(names) else f"tier {tier}"
            lines.append(
                _cap(
                    f"[btd6_cost] {canonical} {name} ({pkey} tier {tier}) — "
                    f"buy E${per['easy']:,}/M${per['medium']:,}"
                    f"/H${per['hard']:,}/I${per['impoppable']:,}; "
                    f"to reach E${cumulative['easy']:,}"
                    f"/M${cumulative['medium']:,}/H${cumulative['hard']:,}"
                    f"/I${cumulative['impoppable']:,}",
                ),
            )
    return lines


def _render_hero(entry: dataset.HeroEntry) -> list[str]:
    canonical = _sanitise(entry.canonical or entry.id)
    bits = []
    if entry.base_cost:
        bits.append(f"base cost: {entry.base_cost} (medium difficulty)")
    meta = " | ".join(bits)
    lines = [
        _cap(
            f"[btd6_hero] {canonical} — {meta} (source: {_dataset_label()})"
            if meta
            else f"[btd6_hero] {canonical} (source: {_dataset_label()})",
        ),
    ]
    for ability in entry.abilities:
        name = _sanitise(str(ability.get("name", "") or ""))
        summary = _sanitise(str(ability.get("summary", "") or ""))
        level = ability.get("level")
        if name and summary:
            lines.append(
                _cap(
                    f"[btd6_hero] {canonical} ability (level {level}): "
                    f"{name} — {summary} (source: {_dataset_label()})",
                ),
            )
    if entry.description:
        lines.append(
            _cap(
                f"[btd6_hero] {canonical} — {_sanitise(entry.description)} "
                f"(source: {_dataset_label()})",
            ),
        )
    return lines


def _render_bloon(entry: dataset.BloonEntry) -> list[str]:
    canonical = _sanitise(entry.canonical or entry.id)
    lines: list[str] = []

    head_bits: list[str] = []
    if entry.category:
        head_bits.append(f"category: {_sanitise(entry.category)}")
    if entry.immune_to:
        head_bits.append(
            "immune to " + ", ".join(_sanitise(d) for d in entry.immune_to),
        )
    elif entry.category not in {"modifier", ""}:
        head_bits.append("no damage-type immunity")
    meta = " | ".join(head_bits)
    lines.append(
        _cap(
            f"[btd6_bloon] {canonical} — {meta} (source: {_dataset_label()})"
            if meta
            else f"[btd6_bloon] {canonical} (source: {_dataset_label()})",
        ),
    )

    stat_bits: list[str] = []
    if entry.properties:
        stat_bits.append(
            "properties: " + ", ".join(_sanitise(p) for p in entry.properties),
        )
    if isinstance(entry.health, int):
        hp = f"health: {entry.health}"
        if isinstance(entry.health_fortified, int):
            hp += f" ({entry.health_fortified} fortified)"
        stat_bits.append(hp)
    if isinstance(entry.rbe, int):
        rbe_bit = f"RBE (total hits incl. all spawned children): {entry.rbe}"
        if isinstance(entry.rbe_fortified, int):
            rbe_bit += f" ({entry.rbe_fortified} fortified)"
        stat_bits.append(rbe_bit)
    if isinstance(entry.speed, (int, float)):
        stat_bits.append(f"speed: {entry.speed}")
    if entry.children:
        stat_bits.append(f"pops into {_sanitise(entry.children)}")
    elif entry.category not in {"modifier", ""}:
        stat_bits.append("pops into nothing (bottom of the spawn chain)")
    if stat_bits:
        lines.append(
            _cap(
                f"[btd6_bloon] {canonical} — {' | '.join(stat_bits)} "
                f"(source: {_dataset_label()})",
            ),
        )
    if entry.description:
        lines.append(
            _cap(
                f"[btd6_bloon] {canonical} — {_sanitise(entry.description)} "
                f"(source: {_dataset_label()})",
            ),
        )
    return lines


def _render_round(number: int, *, abr: bool) -> list[str]:
    raw = dataset.read_blob("abr_rounds.json" if abr else "rounds.json") or {}
    label = "ABR " if abr else ""
    for row in raw.get("rounds", ()):
        if int(row.get("round", -1)) == number:
            bits = [f"{label}Round {number}: {row.get('summary', '')}"]
            if row.get("rbe") is not None:
                bits.append(f"RBE {row['rbe']:,}")
            if row.get("cash") is not None:
                bits.append(f"round cash ${row['cash']:,}")
            return [
                _cap(
                    f"[btd6_round] {' | '.join(_sanitise(b) for b in bits)} "
                    f"(source: {_dataset_label()})",
                ),
            ]
    if abr:
        return [
            f"[btd6_round] Round {number} has no Alternate Bloons Rounds "
            "entry in the dataset — standard-set figures are NOT the ABR "
            "values.",
        ]
    return []


# --- pass 3: paragon name + degree facts -------------------------------------------


def _paragon_name_facts(message_text: str, resolved_tower_ids: set[str]) -> list[str]:
    """A paragon named DIRECTLY ("navarch", "apex plasma master") — the
    resolver doesn't key on paragon names, so ground those too (deduped
    against towers already grounded)."""
    lowered = (message_text or "").lower()
    out: list[str] = []
    for paragon_id in stats.list_paragon_ids():
        pstats = stats.get_paragon_stats(paragon_id)
        if pstats is None or not pstats.canonical:
            continue
        if pstats.canonical.lower() not in lowered:
            continue
        if pstats.tower_id in resolved_tower_ids:
            continue
        cost_bit = f", costing {pstats.cost} on Medium" if pstats.cost else ""
        out.append(
            _cap(
                f"[btd6_paragon] {pstats.canonical} is the {pstats.tower_canonical} "
                f"Paragon (tier 6){cost_bit} (source: bloonswiki)",
            ),
        )
        tower = dataset.get_tower(pstats.tower_id)
        if tower is not None:
            resolved_tower_ids.add(tower.id)
            out.extend(_render_tower(tower))
    return out


def _paragon_degree_facts(message_text: str) -> list[str]:
    """Ground a paragon's stats at a SPECIFIC degree named in the text
    (shipped ``_paragon_degree_facts`` — the BUG-0015 "d67" fix)."""
    degree = keywords.degree_in_text(message_text)
    if degree is None or degree in (1, 100):
        return []
    paragon_id = stats.resolve_paragon_id(message_text)
    if paragon_id is None:
        return []
    pstats = stats.get_paragon_stats(paragon_id)
    if pstats is None or not pstats.has_combat_stats:
        return []
    bits = stats.paragon_main_bits(pstats.base, degree)
    if not bits:
        return []
    src = "bloonswiki article prose" if pstats.is_prose_sourced else "BTD6 game data"
    boss = paragon_degrees.boss_multiplier(degree)
    power = paragon_degrees.power_for_degree(degree)
    return [
        _cap(
            f"[btd6_paragon_stats degree {degree}] {pstats.canonical} at Degree "
            f"{degree}: {_sanitise(', '.join(bits))}; boss-damage ×{boss}; "
            f"{power:,} power (source: {src})",
        ),
        _cap(
            f"[btd6_paragon_stats degree {degree}] Note: 'd{degree}' / "
            f"'degree {degree}' is the paragon's DEGREE (1-100), NOT an "
            "upgrade-path code — paragons are tier 6, beyond the 0-5-5 cap.",
        ),
    ]


# --- pass 4: catalog facts (bosses / powers / MK) ----------------------------------


def _tier_bits(rows) -> list[str]:
    bits = []
    for t in rows or ():
        tier = t.get("tier")
        hp = t.get("health")
        spd = t.get("speed")
        if tier is None or hp is None:
            continue
        bit = f"T{tier} {hp:,} HP"
        if spd is not None:
            bit += f" (speed {spd})"
        bits.append(bit)
    return bits


def _catalog_facts(message_text: str) -> list[str]:
    """Ground powers / Monkey Knowledge / bosses named in the text
    (shipped ``_catalog_facts``; Standard-vs-ELITE labeling is BUG-0002)."""
    import re as _re

    text = (message_text or "").lower()
    if not text:
        return []
    out: list[str] = []

    powers_raw = dataset.read_blob("powers.json") or {}
    for power in powers_raw.get("powers", ()):
        name = str(power.get("canonical", "")).strip().lower()
        if not name or name not in text:
            continue
        bits = [f"cost: {power.get('monkey_money_cost')} Monkey Money"]
        if power.get("quantity"):
            bits.append(f"max {power['quantity']} per game")
        if power.get("between_rounds"):
            bits.append("usable between rounds")
        out.append(
            _cap(
                f"[btd6_power] {power.get('canonical')} (power) — "
                f"{_sanitise(power.get('description', ''))} ({'; '.join(bits)})",
            ),
        )

    if "knowledge" in text or _re.search(r"\bmk\b", text):
        mk_raw = dataset.read_blob("monkey_knowledge.json") or {}
        for entry in mk_raw.get("knowledge", ()):
            name = str(entry.get("canonical", "")).strip().lower()
            if not name or name not in text:
                continue
            line = (
                f"[btd6_knowledge] {entry.get('canonical')} "
                f"({entry.get('category')} tree, Monkey Knowledge) — "
                f"{_sanitise(entry.get('description', ''))}"
            )
            prereqs = entry.get("prerequisites") or ()
            if prereqs:
                line += f" | requires: {', '.join(prereqs)}"
            out.append(_cap(line))

    for boss in dataset.bosses():
        name = boss.canonical.strip().lower()
        if not name or name not in text:
            continue
        blurb = _sanitise(boss.tagline or boss.description)
        line = f"[btd6_boss] {boss.canonical} (boss bloon) — {blurb}"
        if boss.immune_to:
            line += f" | immune to: {', '.join(boss.immune_to)}"
        if boss.tiers:
            line += f" | {len(boss.tiers)} tier(s) on record"
        out.append(_cap(line))
        standard_bits = _tier_bits(boss.tiers)
        if standard_bits:
            out.append(
                _cap(
                    f"[btd6_boss] {boss.canonical} per-tier health — Standard "
                    "(non-Elite) ranked boss, single-player: "
                    + " · ".join(standard_bits),
                ),
            )
        if "elite" in text:
            elite_bits = _tier_bits(boss.elite_tiers)
            if elite_bits:
                out.append(
                    _cap(
                        f"[btd6_boss] ELITE {boss.canonical} per-tier health "
                        "(single-player): "
                        + " · ".join(elite_bits)
                        + " — answer Elite questions from these figures, NOT "
                        "from the Standard table.",
                    ),
                )
            else:
                out.append(
                    _cap(
                        f"[btd6_boss] Elite {boss.canonical} health is NOT in "
                        "the dataset — only standard-tier health is on record.",
                    ),
                )
    return out


# --- the build entry point ---------------------------------------------------------


async def build(
    message_text: str,
    *,
    guild_id: int | None = None,
    channel_id: int | None = None,
    conversation_followup: bool = False,
) -> BTD6Context:
    """Build a BTD6 context bundle for ``message_text`` (each pass
    isolated; a failing pass logs and never suppresses the others)."""
    facts: list[str] = []
    confidence = 0.0

    intent = None
    try:
        intent = resolver.resolve(message_text)
        confidence = intent.confidence
    except Exception:  # noqa: BLE001 — defensive (shipped)
        logger.debug("btd6 context: resolver unavailable", exc_info=True)

    resolved_tower_ids: set[str] = set()
    if intent is not None:
        try:
            for tower in intent.towers:
                resolved_tower_ids.add(tower.id)
                facts.extend(_render_tower(tower))
            for hero in intent.heroes:
                facts.extend(_render_hero(hero))
            for bloon in intent.bloons:
                facts.extend(_render_bloon(bloon))
            abr_cue = bool(keywords.ABR_CUE_RE.search(message_text or ""))
            for number in intent.candidate_round_numbers:
                facts.extend(_render_round(number, abr=abr_cue))
        except Exception:  # noqa: BLE001
            logger.debug("btd6 context: fixture pass failed", exc_info=True)

        try:
            facts.extend(_paragon_name_facts(message_text, resolved_tower_ids))
        except Exception:  # noqa: BLE001
            logger.debug("btd6 context: paragon-name pass failed", exc_info=True)

        try:
            facts.extend(_paragon_degree_facts(message_text))
        except Exception:  # noqa: BLE001
            logger.debug("btd6 context: paragon-degree pass failed", exc_info=True)

        try:
            facts.extend(_catalog_facts(message_text))
        except Exception:  # noqa: BLE001
            logger.debug("btd6 context: catalog pass failed", exc_info=True)

        try:
            facts.extend(interactions.interaction_facts(message_text))
        except Exception:  # noqa: BLE001
            logger.debug("btd6 context: interaction pass failed", exc_info=True)

    if facts:
        facts.append(
            "[btd6_coverage] Facts above come from the committed BTD6 "
            f"dataset (game version {dataset.game_version()}); live-event "
            "data (current boss/race/CT/odyssey) is not loaded — do not "
            "answer live-event questions from memory.",
        )

    return BTD6Context(
        facts=tuple(facts),
        source_summary=(
            _DATASET_SOURCE_SUMMARY if facts else _FALLBACK_SOURCE_SUMMARY
        ),
        confidence=confidence,
    )

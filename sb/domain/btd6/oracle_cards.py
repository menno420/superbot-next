"""BTD6 oracle-surface CARDS (band 7) — the shipped ``!btd6`` reply embeds,
byte-for-byte.

Every builder here is a focused port of the shipped formatter that produced
the goldens/btd6 corpus (oracle @7f7628e1):

* ``cogs/btd6/_embeds.py``  — status / diagnostics / test-intent;
* ``cogs/btd6/_builders.py`` — income / rbe / round (+ range tables),
  tower / hero / estimate / relic / CT browser / CT team / live events /
  event detail / leaderboard / refresh-source / source-health /
  latest-data / grounding / why-no-response / strategies / sources;
* ``cogs/btd6/_ops_helpers.py`` — readiness / runs / toggle / announce;
* ``services/btd6_response_builder.py`` + ``utils/btd6/response_embed.py``
  — the BTD6Response shape and its embed rendering;
* ``utils/btd6/context_footer.py`` — the `` • ctx=…`` footer contract;
* ``views/btd6/panel.py`` — the hub embed (+ its button roster, consumed
  by sb/domain/btd6/panels.py).

Builders return :class:`~sb.kernel.panels.render.RenderedEmbed` (or plain
strings for the shipped content-only replies) — presentation-free and
side-effect-free; the handlers in sb/domain/btd6/oracle_surface.py own the
sends. Live-ingestion state (btd6_facts / source registry / ingestion
runs) is the D-0046 successor port: with no sources registered and no
facts ingested, every builder renders the shipped EMPTY state — which is
also this build's true state, so the copy stays honest.

Deviations from the oracle, ledgered here (all on golden-UNPINNED paths):
* freeplay MOAB scaling (effective RBE, rounds 81+) is not recomputed —
  RBE renders the wiki base only (the scaled recompute needs the spawn-
  tree walk of ``bloon_rbe_at_round``, a named successor);
* the boss-fight estimator (`!btd6 estimate <query>`) is a successor —
  only the golden-pinned bare-usage card is served.

(The resolver's maps/modes matching — formerly the third ledgered
deviation — is PORTED: the resolver matches them, ``deterministic_answer``
answers them in the shipped order via :func:`for_map` / :func:`for_mode`,
and test-intent renders the matched canonicals. In the oracle, matched
maps/modes additionally feed the ``btd6_facts`` DB grounding pass — that
pass rides D-0046 with the rest of live ingestion.)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sb.domain.btd6 import dataset
from sb.kernel.panels.render import RenderedEmbed

__all__ = [
    "BTD6Response",
    "append_ctx",
    "response_embed",
]

# the shipped capture-time dataset label (btd6_data_service.data_source_label
# for the local file backend). The committed corpus IS that directory copied
# file-for-file (sb/domain/btd6/data/, provenance btd6_data_blobs.sha256 —
# dataset.py module docstring), so the label stays the truthful provenance
# statement the goldens pin.
DATA_SOURCE_LABEL = "local:disbot/data/btd6"

_MAP_DIFFICULTY_ORDER = ("Beginner", "Intermediate", "Advanced", "Expert")

#: shipped copy — btd6_data_service._CASH_ASSUMPTIONS, verbatim.
CASH_ASSUMPTIONS = (
    "Standard (default) round set, Medium difficulty ($650 start), no income "
    "towers. Per-round cash is pop cash (v55 income decay) plus the "
    "$100 + round end-of-round bonus. Cash modifiers (Double Cash, Half Cash) "
    "and other difficulties or round sets (e.g. ABR) are not applied."
)

_ROUND_DETAIL_CAP = 40


# ---------------------------------------------------------------------------
# dataset views (rounds / xp / relics / maps / modes — read_blob passes)
# ---------------------------------------------------------------------------


def data_version() -> str:
    raw = dataset.read_blob("towers.json") or {}
    return str(raw.get("data_version", "") or "unknown")


def source_label() -> str:
    """``BTD6 data v1.0 (game v55.1)`` — response_builder._source_label."""
    return f"BTD6 data v{data_version()} (game v{dataset.game_version()})"


def default_rounds() -> list[dict]:
    raw = dataset.read_blob("rounds.json") or {}
    return [r for r in raw.get("rounds", ())
            if r.get("roundset", "default") == "default"]


def get_round(number: int) -> dict | None:
    for row in default_rounds():
        if int(row.get("round", -1)) == number:
            return row
    return None


def round_base_xp(number: int) -> int | None:
    raw = dataset.read_blob("round_xp.json") or {}
    for row in raw.get("rounds", ()):
        if int(row.get("round", -1)) == number:
            value = row.get("xp")
            return int(value) if value is not None else None
    return None


def list_maps() -> list[dict]:
    raw = dataset.read_blob("maps.json") or {}
    return list(raw.get("maps", ()))


def list_modes() -> list[dict]:
    raw = dataset.read_blob("modes.json") or {}
    return list(raw.get("modes", ()))


def list_relics() -> list[dict]:
    raw = dataset.read_blob("ct_relics.json") or {}
    return list(raw.get("relics", ()))


def resolve_relic(term: str) -> dict | None:
    """btd6_data_service.resolve_relic — id / api_name / canonical /
    abbrev / alias, case-insensitive."""
    needle = (term or "").strip().lower()
    if not needle:
        return None
    for relic in list_relics():
        candidates = {
            str(relic.get("id", "")).lower(),
            str(relic.get("api_name", "")).lower(),
            str(relic.get("canonical", "")).lower(),
            *(str(a).lower() for a in relic.get("aliases", ()) or ()),
        }
        if relic.get("abbrev"):
            candidates.add(str(relic["abbrev"]).lower())
        if needle in candidates:
            return relic
    return None


# ---------------------------------------------------------------------------
# per-round economy (btd6_data_service.round_cash / round_rbe, default set)
# ---------------------------------------------------------------------------


def round_cash(round_start: int, round_end: int | None = None) -> dict:
    """The shipped structured round-cash contract (default set, Medium)."""
    lo = round_start
    hi = round_start if round_end is None else round_end
    normalized = lo > hi
    if normalized:
        lo, hi = hi, lo
    cash_rounds = [r for r in default_rounds() if r.get("cash") is not None]
    if not cash_rounds:
        return {"found": False, "reason": "no_cash_data",
                "note": "no standard round cash data is loaded"}
    available = {int(r["round"]) for r in cash_rounds}
    valid_min, valid_max = min(available), max(available)
    in_range = [r for r in cash_rounds if lo <= int(r["round"]) <= hi]
    if not in_range:
        return {"found": False, "reason": "invalid_range",
                "round_start": lo, "round_end": hi,
                "note": (f"no standard rounds in {lo}-{hi} "
                         f"(valid {valid_min}-{valid_max})")}
    missing = [n for n in range(lo, hi + 1) if n not in available]
    if missing:
        return {"found": False, "reason": "cash_unavailable",
                "round_start": lo, "round_end": hi,
                "note": (f"cash data is only available for rounds "
                         f"{valid_min}-{valid_max}; missing: {missing[:10]}")}
    by_n = {int(r["round"]): r for r in cash_rounds}
    if lo == hi:
        entry = by_n[lo]
        return {"found": True, "single_round": True,
                "round_start": lo, "round_end": hi,
                "round_cash": entry["cash"],
                "cumulative_cash": entry.get("cumulative_cash"),
                "assumptions": CASH_ASSUMPTIONS}
    range_cash = round(sum(float(r["cash"]) for r in in_range), 2)
    per_round = [{"round": int(r["round"]), "cash": r["cash"],
                  "cumulative_cash": r.get("cumulative_cash")}
                 for r in in_range[:_ROUND_DETAIL_CAP]]
    return {"found": True, "single_round": False,
            "round_start": lo, "round_end": hi,
            "rounds_counted": hi - lo + 1, "range_cash": range_cash,
            "per_round": per_round,
            "truncated": len(in_range) > _ROUND_DETAIL_CAP,
            "assumptions": CASH_ASSUMPTIONS}


def round_rbe(round_start: int, round_end: int | None = None) -> dict:
    """Wiki-base RBE (default set). The freeplay effective recompute
    (rounds 81+ MOAB scaling + superceramics) is a ledgered successor —
    ``scaled`` is always False here, so the render never CLAIMS a scaled
    figure it did not compute."""
    lo = round_start
    hi = round_start if round_end is None else round_end
    if lo > hi:
        lo, hi = hi, lo
    rbe_rounds = [r for r in default_rounds() if r.get("rbe") is not None]
    if not rbe_rounds:
        return {"found": False, "reason": "no_rbe_data",
                "note": "no standard round RBE data is loaded"}
    available = {int(r["round"]) for r in rbe_rounds}
    valid_min, valid_max = min(available), max(available)
    in_range = [r for r in rbe_rounds if lo <= int(r["round"]) <= hi]
    if not in_range:
        return {"found": False, "reason": "invalid_range",
                "round_start": lo, "round_end": hi,
                "note": (f"no standard rounds in {lo}-{hi} "
                         f"(valid {valid_min}-{valid_max})")}
    missing = [n for n in range(lo, hi + 1) if n not in available]
    if missing:
        return {"found": False, "reason": "rbe_unavailable",
                "round_start": lo, "round_end": hi,
                "note": (f"RBE data is only available for rounds "
                         f"{valid_min}-{valid_max}; missing: {missing[:10]}")}
    by_n = {int(r["round"]): r for r in rbe_rounds}
    if lo == hi:
        return {"found": True, "single_round": True, "round": lo,
                "base_rbe": int(by_n[lo]["rbe"]), "effective_rbe": None,
                "scaled": False}
    per_round = [{"round": int(r["round"]), "base_rbe": int(r["rbe"]),
                  "effective_rbe": None}
                 for r in in_range[:_ROUND_DETAIL_CAP]]
    return {"found": True, "single_round": False,
            "round_start": lo, "round_end": hi,
            "rounds_counted": hi - lo + 1,
            "base_rbe_total": sum(int(r["rbe"]) for r in in_range),
            "effective_rbe_total": None, "scaled": False,
            "per_round": per_round,
            "truncated": len(in_range) > _ROUND_DETAIL_CAP}


# ---------------------------------------------------------------------------
# BTD6Response + its embed render (response_builder + response_embed)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BTD6Response:
    """services/btd6_response_builder.BTD6Response, verbatim shape."""

    title: str
    short_answer: str
    why_it_matters: str = ""
    recommended_options: tuple[str, ...] = ()
    common_mistakes: tuple[str, ...] = ()
    version_sensitivity: str = ""
    confidence: str = "medium"
    sources: tuple[str, ...] = ()
    follow_up: str = ""
    fields: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    live_facts: tuple[str, ...] = ()


#: the one string the unresolved path is recognised by.
UNRESOLVED_TITLE = "No BTD6 entities recognised"

_CONFIDENCE_TOKEN = {"high": "green", "medium": "gold", "low": "light_grey"}


def response_embed(response: BTD6Response) -> RenderedEmbed:
    """utils/btd6/response_embed.response_to_embed, over RenderedEmbed."""
    fields: list[tuple[str, str, bool]] = []
    if response.why_it_matters:
        fields.append(("Why it matters", response.why_it_matters, False))
    for name, value in response.fields:
        if value:
            fields.append((name, str(value)[:1024], False))
    if response.recommended_options:
        fields.append(("Recommended options",
                       "\n".join(f"• {opt}"
                                 for opt in response.recommended_options),
                       False))
    if response.common_mistakes:
        fields.append(("Common mistakes",
                       "\n".join(f"• {m}" for m in response.common_mistakes),
                       False))
    if response.version_sensitivity:
        fields.append(("Version sensitivity", response.version_sensitivity,
                       False))
    if response.live_facts:
        value = "\n".join(f"• {fact}" for fact in response.live_facts)
        if len(value) > 1024:
            kept: list[str] = []
            running = 0
            for fact in response.live_facts:
                line = f"• {fact}"
                if running + len(line) + 1 > 990:
                    break
                kept.append(line)
                running += len(line) + 1
            dropped = len(response.live_facts) - len(kept)
            value = "\n".join(kept) + f"\n… ({dropped} more)"
        fields.append(("Live data", value, False))
    if response.follow_up:
        fields.append(("Follow-up", response.follow_up, False))
    return RenderedEmbed(
        title=response.title, description=response.short_answer,
        fields=tuple(fields),
        footer=" · ".join(response.sources) if response.sources else "",
        style_token=_CONFIDENCE_TOKEN.get(response.confidence, "light_grey"))


def append_ctx(embed: RenderedEmbed, context_id: str) -> RenderedEmbed:
    """utils/btd6/context_footer.append_context_footer over RenderedEmbed."""
    from dataclasses import replace

    existing = embed.footer or ""
    segment = f" • ctx={context_id}"
    if existing.endswith(segment):
        return embed
    marker = existing.rfind(" • ctx=")
    if marker != -1:
        existing = existing[:marker]
    text = f"{existing}{segment}" if existing else f"ctx={context_id}"
    return replace(embed, footer=text)


# --- response builders (services/btd6_response_builder.py) -------------------


def for_unresolved(confidence: float) -> BTD6Response:
    return BTD6Response(
        title=UNRESOLVED_TITLE,
        short_answer=("I couldn't find a tower, hero, map, mode, round, or "
                      "bloon in your message."),
        why_it_matters=(
            f"Confidence: {confidence:.2f}. Try mentioning a tower "
            "by name (e.g. ``Dart Monkey``), a map, a bloon, a power, or a "
            "round number like ``round 63``."),
        confidence="low",
        sources=(source_label(),),
        follow_up="Use `!btd6 status` to confirm the BTD6 assistant is enabled.",
    )


_PATH_LABELS = {"top": "Top path", "mid": "Middle path", "bot": "Bottom path"}


def _format_upgrade_path(tiers: tuple[str, ...], costs: tuple[int, ...]) -> str:
    parts: list[str] = []
    for index, name in enumerate(tiers):
        cost = costs[index] if index < len(costs) else 0
        parts.append(f"{name} (${cost:,})" if cost > 0 else name)
    return " → ".join(parts)


def for_tower(tower: dataset.TowerEntry) -> BTD6Response:
    path_fields: list[tuple[str, str]] = []
    for path, tiers in tower.upgrade_paths.items():
        if not tiers:
            continue
        label = _PATH_LABELS.get(path, f"{path.title()} path")
        costs = tower.upgrade_costs.get(path, ())
        path_fields.append((label, _format_upgrade_path(tiers, costs)))
    base_cost = int(tower.base_cost or 0)
    short_answer = tower.description or (
        f"A {tower.category} tower costing ${base_cost:,} to place. "
        "Upgrade paths and per-tier costs are listed below.")
    return BTD6Response(
        title=f"{tower.canonical} — overview",
        short_answer=short_answer,
        why_it_matters=(f"Base cost: ${base_cost:,}. "
                        f"Category: {tower.category.title()}."),
        fields=tuple(path_fields),
        common_mistakes=(
            "Buying high-tier upgrades on the wrong path can stall economy.",),
        version_sensitivity=(
            "Tower stats and crosspath interactions can change patch-to-patch; "
            "always confirm against the latest patch notes for competitive "
            "play."),
        confidence="high",
        sources=(source_label(),),
        follow_up="Ask about a specific upgrade tier with `!btd6 tower <name>`.",
    )


def for_hero(hero: dataset.HeroEntry) -> BTD6Response:
    abilities = tuple(
        f"L{a.get('level')}: {a.get('name')} — {a.get('summary')}"
        for a in hero.abilities)
    return BTD6Response(
        title=f"{hero.canonical} — overview",
        short_answer=hero.description,
        why_it_matters=f"Base cost: {hero.base_cost}.",
        recommended_options=abilities,
        version_sensitivity=(
            "Hero balance changes are common; check patch notes for "
            "buffs/nerfs."),
        confidence="medium",
        sources=(source_label(),),
        follow_up="Try `!btd6 round <N>` to see what waves the hero faces.",
    )


def for_round(entry: dict) -> BTD6Response:
    number = int(entry.get("round", 0))
    economy_bits: list[str] = []
    if entry.get("rbe") is not None:
        economy_bits.append(f"RBE **{int(entry['rbe']):,}**")
    if entry.get("cash") is not None:
        cumulative = entry.get("cumulative_cash")
        cum = (f" (cumulative **${cumulative:,.0f}**)"
               if cumulative is not None else "")
        economy_bits.append(f"Cash **${float(entry['cash']):,.0f}**{cum}")
    base_xp = round_base_xp(number)
    if base_xp is not None:
        economy_bits.append(f"XP **{base_xp:,}**")
    fields: tuple[tuple[str, str], ...] = (
        (("Economy", " · ".join(economy_bits)),) if economy_bits else ())
    threats = tuple(str(t) for t in entry.get("common_threats", ()) or ())
    return BTD6Response(
        title=f"Round {number} — danger: {entry.get('danger', '')}",
        short_answer=str(entry.get("summary", "")),
        why_it_matters=("Threats this round: "
                        + (", ".join(threats) if threats else "—")),
        fields=fields,
        version_sensitivity=(
            "Round composition is stable but can shift slightly during major "
            "patches."),
        confidence="high",
        sources=(source_label(),),
        follow_up="Use `!btd6 ask` for strategy advice on a specific round.",
    )


def for_map(game_map: dataset.MapEntry) -> BTD6Response:
    why = game_map.lines_of_sight_notes
    # Removable obstacles ride alongside line-of-sight (most removables ARE
    # LoS blockers). Only present for maps with curated data; absent =
    # unknown. (Shipped comment + logic, btd6_response_builder.for_map.)
    if game_map.removables:
        why = f"{why} Removable obstacles: {game_map.removables}"
    return BTD6Response(
        title=f"{game_map.canonical} ({game_map.difficulty})",
        short_answer=game_map.description,
        why_it_matters=why,
        sources=(source_label(),),
        confidence="high",
        follow_up="Pair with `!btd6 mode <name>` for mode-specific advice.",
    )


def for_mode(mode: dataset.ModeEntry) -> BTD6Response:
    # Modifiers (Double Cash, Fast Track) have no fixed cash/lives — their
    # effect is relative — so only state those numbers when the row carries
    # them. (Shipped comment + logic, btd6_response_builder.for_mode.)
    bits: list[str] = []
    if mode.starting_cash is not None:
        bits.append(f"Starting cash: {mode.starting_cash}.")
    if mode.starting_lives is not None:
        bits.append(f"Starting lives: {mode.starting_lives}.")
    return BTD6Response(
        title=f"{mode.canonical} mode",
        short_answer=mode.description,
        why_it_matters=" ".join(bits),
        recommended_options=mode.restrictions,
        confidence="high",
        sources=(source_label(),),
    )


def for_bloon(bloon: dataset.BloonEntry) -> BTD6Response:
    stat_bits: list[str] = []
    if bloon.health is not None:
        fortified = (f" ({bloon.health_fortified} fortified)"
                     if bloon.health_fortified is not None else "")
        stat_bits.append(f"Health: {bloon.health}{fortified}")
    if bloon.rbe is not None:
        fortified = (f" ({bloon.rbe_fortified} fortified)"
                     if bloon.rbe_fortified is not None else "")
        stat_bits.append(f"RBE: {bloon.rbe}{fortified}")
    if bloon.speed is not None:
        stat_bits.append(f"Speed: {bloon.speed:g}")
    options: list[str] = []
    if bloon.children:
        options.append(f"Pops into: {bloon.children}")
    if bloon.immune_to:
        options.append(f"Immune to: {', '.join(bloon.immune_to)}")
    if bloon.properties:
        options.append(f"Properties: {', '.join(bloon.properties)}")
    return BTD6Response(
        title=f"{bloon.canonical} — bloon ({bloon.category})",
        short_answer=bloon.description,
        why_it_matters=" · ".join(stat_bits),
        recommended_options=tuple(options),
        confidence="high",
        sources=(source_label(),),
        follow_up="Ask about a specific round to see where this bloon appears.",
    )


def for_reference_facts(facts: tuple[str, ...]) -> BTD6Response:
    headline = facts[0]
    if headline.startswith("[") and "] " in headline:
        headline = headline.split("] ", 1)[1]
    return BTD6Response(
        title="BTD6 reference",
        short_answer=headline,
        why_it_matters=(f"Matched {len(facts)} verified fact(s) from the "
                        "BTD6 dataset (full list below)."),
        confidence="medium",
        sources=(source_label(),),
        live_facts=facts,
    )


def deterministic_answer(intent) -> BTD6Response:
    """btd6_ai_service.deterministic_answer over the ported resolver.

    First recognised entity wins, shipped order: towers → heroes → maps
    → modes → rounds → bloons. (The oracle round-trips ``intent.maps[0]``
    through ``map_fact``/``mode_fact`` — knowledge_service delegates
    straight to the dataset ``get_map``/``get_mode``, so the resolved
    entry IS the fact; the tower/hero branches here carry the same
    collapse.)"""
    if intent.towers:
        return for_tower(intent.towers[0])
    if intent.heroes:
        return for_hero(intent.heroes[0])
    if intent.maps:
        return for_map(intent.maps[0])
    if intent.modes:
        return for_mode(intent.modes[0])
    if intent.candidate_round_numbers:
        entry = get_round(int(intent.candidate_round_numbers[0]))
        if entry is not None:
            return for_round(entry)
    if intent.bloons:
        return for_bloon(intent.bloons[0])
    return for_unresolved(intent.confidence)


# ---------------------------------------------------------------------------
# command cards — every shipped `!btd6 <sub>` embed
# ---------------------------------------------------------------------------


async def ask_card(text: str) -> RenderedEmbed:
    """`!btd6 ask <q>` — deterministic answer + best-effort grounding
    (btd6_ai_service.answer_question, deterministic legs only: the AI
    augmentation gate is the K10 platform's, off in this surface)."""
    from dataclasses import replace

    from sb.domain.btd6 import context, resolver

    intent = resolver.resolve(text)
    response = deterministic_answer(intent)
    try:
        ctx = await context.build(text)
        facts = tuple(ctx.facts)
    except Exception:  # noqa: BLE001 — grounding is best-effort, shipped
        facts = ()
    if facts:
        if response.title == UNRESOLVED_TITLE:
            response = for_reference_facts(facts)
        else:
            response = replace(response, live_facts=facts)
    return response_embed(response)


def tower_card(name: str) -> RenderedEmbed:
    from sb.domain.btd6 import resolver

    intent = resolver.resolve(name)
    if not intent.towers:
        return response_embed(deterministic_answer(intent))
    tower = intent.towers[0]
    return append_ctx(response_embed(for_tower(tower)),
                      f"btd6_tower:{tower.id}")


def hero_card(name: str) -> RenderedEmbed:
    from sb.domain.btd6 import resolver

    intent = resolver.resolve(name)
    if not intent.heroes:
        return response_embed(deterministic_answer(intent))
    hero = intent.heroes[0]
    embed = response_embed(for_hero(hero))
    # the shipped hero card adds the hero-stats coverage line; the stats
    # coverage registry is a successor — the base card is the pinned shape.
    return append_ctx(embed, f"btd6_hero:{hero.id}")


def _elide(rows: list, head: int = 11, tail: int = 9) -> tuple[list, bool]:
    if len(rows) <= head + tail + 1:
        return rows, False
    return rows[:head] + rows[-tail:], True


def _code_table(header: str, rule: str, body_lines: list[str]) -> str:
    return "```\n" + "\n".join([header, rule, *body_lines]) + "\n```"


def income_card(round_start: int, round_end: int | None = None) -> RenderedEmbed:
    res = round_cash(round_start, round_end)
    if not res.get("found"):
        return RenderedEmbed(
            title="🐵 BTD6 income — no data",
            description=res.get("note") or "No cash data for that round range.",
            style_token="red")
    assumptions = res.get("assumptions") or "Standard/Medium, no income towers."
    if res.get("single_round"):
        cumulative = res.get("cumulative_cash")
        cum = (f" (cumulative **${cumulative:,.0f}**)"
               if cumulative is not None else "")
        return RenderedEmbed(
            title=f"🐵 BTD6 income — round {res['round_start']}",
            description=f"Earns **${res['round_cash']:,.1f}**{cum} this round.",
            footer=assumptions, style_token="green")
    lo, hi = res["round_start"], res["round_end"]
    rows, elided = _elide(res.get("per_round", []))
    body = [
        f"{('r' + str(r['round'])):>5} │ {r['cash']:>9,.1f} │ "
        f"{r['cumulative_cash']:>11,.0f}"
        for r in rows
    ]
    if elided:
        body.insert(len(body) - 9, f"{'⋮':>5} │ {'⋮':>9} │ {'⋮':>11}")
    table = _code_table(
        f"{'round':>5} │ {'cash':>9} │ {'cumulative':>11}",
        "──────┼───────────┼─────────────", body)
    note = assumptions
    if res.get("truncated"):
        note += " · breakdown truncated; total is the full range"
    return RenderedEmbed(
        title=f"🐵 BTD6 income — rounds {lo}–{hi}",
        description=(f"You earn **${res['range_cash']:,.0f}** across rounds "
                     f"{lo}–{hi} ({res['rounds_counted']} rounds, both "
                     f"endpoints).\n{table}"),
        footer=note, style_token="green")


def rbe_card(round_start: int, round_end: int | None = None) -> RenderedEmbed:
    res = round_rbe(round_start, round_end)
    if not res.get("found"):
        return RenderedEmbed(
            title="🐵 BTD6 RBE — no data",
            description=res.get("note") or "No RBE data for that round range.",
            style_token="red")
    if res.get("single_round"):
        return RenderedEmbed(
            title=f"🐵 BTD6 RBE — round {res['round']}",
            description=f"**{res['base_rbe']:,}** RBE",
            style_token="blue")
    lo, hi = res["round_start"], res["round_end"]
    rows, elided = _elide(res.get("per_round", []))
    body = [f"{('r' + str(r['round'])):>5} │ {r['base_rbe']:>12,}" for r in rows]
    if elided:
        body.insert(len(body) - 9, f"{'⋮':>5} │ {'⋮':>12}")
    table = _code_table(
        f"{'round':>5} │ {'RBE':>12}", "──────┼──────────────", body)
    totals = f"Total RBE — **{res['base_rbe_total']:,}**"
    return RenderedEmbed(
        title=f"🐵 BTD6 RBE — rounds {lo}–{hi}",
        description=f"{totals} across {res['rounds_counted']} rounds.\n{table}",
        style_token="blue")


_MOD_TAGS = ("fortified", "regrow", "camo")


def _format_composition(groups: list[dict]) -> str:
    lines = []
    for g in groups[:25]:
        bloon = dataset.get_bloon(str(g.get("bloon_id")))
        name = bloon.canonical if bloon is not None else str(g.get("bloon_id"))
        mods = [m for m in _MOD_TAGS if m in (g.get("modifiers") or ())]
        suffix = f" — {', '.join(mods)}" if mods else ""
        lines.append(f"`{int(g.get('count', 0)):>5,}×` {name}{suffix}")
    if len(groups) > 25:
        lines.append(f"…and {len(groups) - 25} more groups")
    return "\n".join(lines) or "—"


def round_card(number: int, end_round: int | None = None) -> RenderedEmbed:
    from dataclasses import replace
    from sb.domain.btd6 import resolver

    if end_round is not None and end_round != number:
        return _round_range_card(number, end_round)
    entry = get_round(number)
    if entry is None:
        return response_embed(
            for_unresolved(resolver.resolve(f"round {number}").confidence))
    embed = response_embed(for_round(entry))
    groups = list(entry.get("groups", ()) or ())
    if groups:
        total = sum(int(g.get("count", 0)) for g in groups)
        embed = replace(embed, fields=embed.fields + (
            (f"Bloons this round — {total:,} spawned",
             _format_composition(groups), False),))
    return embed


def _round_range_card(round_start: int, round_end: int) -> RenderedEmbed:
    lo, hi = ((round_start, round_end) if round_start <= round_end
              else (round_end, round_start))
    rbe = round_rbe(lo, hi)
    if not rbe.get("found"):
        return RenderedEmbed(
            title="🐵 BTD6 rounds — no data",
            description=rbe.get("note") or "No round data for that range.",
            style_token="red")
    cash = round_cash(lo, hi)
    rbe_by_round = {r["round"]: r["base_rbe"] for r in rbe.get("per_round", [])}
    cash_by_round = {r["round"]: r
                     for r in (cash.get("per_round", [])
                               if cash.get("found") else [])}
    rounds = sorted(rbe_by_round)
    shown, elided = _elide(rounds)
    body = []
    for rn in shown:
        rbe_v = rbe_by_round.get(rn)
        crow = cash_by_round.get(rn, {})
        rbe_s = f"{rbe_v:,}" if rbe_v is not None else "—"
        cash_s = (f"${crow['cash']:,.0f}"
                  if crow.get("cash") is not None else "—")
        cum_s = (f"${crow['cumulative_cash']:,.0f}"
                 if crow.get("cumulative_cash") is not None else "—")
        body.append(f"{'r' + str(rn):>5} │ {rbe_s:>11} │ {cash_s:>9} │ "
                    f"{cum_s:>11}")
    if elided:
        body.insert(len(body) - 9, f"{'⋮':>5} │ {'⋮':>11} │ {'⋮':>9} │ {'⋮':>11}")
    table = _code_table(
        f"{'round':>5} │ {'RBE':>11} │ {'cash':>9} │ {'cumulative':>11}",
        "──────┼─────────────┼───────────┼─────────────", body)
    head = f"**Rounds {lo}–{hi}** — total RBE **{rbe['base_rbe_total']:,}**"
    if cash.get("found") and cash.get("range_cash") is not None:
        head += f", total cash **${cash['range_cash']:,.0f}**"
    footer = ["Standard/Medium, no income towers"]
    if rbe.get("truncated") or (cash.get("found") and cash.get("truncated")):
        footer.append("breakdown truncated; totals are the full range")
    return RenderedEmbed(
        title=f"🐵 BTD6 rounds {lo}–{hi}",
        description=f"{head}\n{table}",
        footer=" · ".join(footer), style_token="blurple")


def estimate_usage_card() -> RenderedEmbed:
    return RenderedEmbed(
        title="🎯 BTD6 boss-fight estimate",
        description=(
            "Estimate a boss fight from grounded HP/DPS/cost:\n"
            "• `<tower> vs <boss> [tier]` — e.g. "
            "`super monkey 0-4-0 vs bloonarius t5`\n"
            "• `counters <boss> [tier]` — the most cost-efficient towers"),
        style_token="blurple")


def relic_card(name: str) -> RenderedEmbed:
    relic = resolve_relic(name)
    if relic is None:
        names = ", ".join(
            sorted(str(r.get("canonical", "")) for r in list_relics())[:8])
        return RenderedEmbed(
            title="🗺️ BTD6 CT — Unknown relic",
            description=(f"`{name}` isn't a relic I know. Examples: {names}…"
                         if names else f"`{name}` isn't a relic I know."),
            style_token="red")
    abbrev = str(relic.get("abbrev", "") or "")
    canonical = str(relic.get("canonical", "") or relic.get("id", ""))
    display = f"{canonical} ({abbrev})" if abbrev else canonical
    embed = RenderedEmbed(
        title=f"🗺️ CT Relic — {display}",
        description=str(relic.get("effect", "") or ""),
        fields=(("Category", str(relic.get("category", "") or ""), True),
                ("On the map now",
                 "No active CT tile currently carries this relic (or live "
                 "data isn't loaded).", False)),
        footer="Source: bloonswiki + data.ninjakiwi.com",
        style_token="teal")
    return append_ctx(embed, f"btd6_ct_relic:{relic.get('id')}")


def ct_browser_card() -> RenderedEmbed:
    embed = RenderedEmbed(
        title="🗺️ BTD6 — Contested Territory",
        description=("No active CT events recorded. Try "
                     "`!btd6 refresh-source nk_btd6_ct` to fetch live data."),
        style_token="gold")
    return append_ctx(embed, "btd6_ct:browser")


def ctteam_card() -> RenderedEmbed:
    embed = RenderedEmbed(
        title="🛡️ BTD6 — Your CT Team",
        description=(
            "No CT team is set for this server.\n"
            "An admin can set one with `!btd6 ctteam <bracket id or group "
            "URL>` — copy your team's `…/leaderboard/group/<id>` link from "
            "the CT team leaderboard."),
        style_token="gold")
    return append_ctx(embed, "btd6_ct:team")


# --- status / diagnostics / test-intent (cogs/btd6/_embeds.py) ---------------


_NO_FACTS_COPY = ("No facts ingested yet. Run `!btd6 refresh-source <key>` "
                  "or wait for the next supervisor cycle.")


def status_card() -> RenderedEmbed:
    embed = RenderedEmbed(
        title="🐵 BTD6 Assistant — Status",
        description=("Deterministic facts plus live grounding for matched "
                     "intents. Natural-language replies are gated by the "
                     "AI Platform."),
        fields=(
            ("📚 Reference (seed)",
             f"Data version: `{data_version()}` · "
             f"Game version: `{dataset.game_version()}`\n"
             f"Towers: **{len(dataset.towers())}** · "
             f"Heroes: **{len(dataset.heroes())}** · "
             f"Maps: **{len(list_maps())}** · "
             f"Modes: **{len(list_modes())}** · "
             f"Rounds: **{len(default_rounds())}**", False),
            ("📊 Live facts (btd6_facts)", _NO_FACTS_COPY, False),
            ("🗄️ Data source", f"`{DATA_SOURCE_LABEL}`", False),
        ),
        style_token="green")
    return append_ctx(embed, "btd6_status:global")


def diagnostics_card() -> RenderedEmbed:
    maps = list_maps()
    by_difficulty: dict[str, int] = {}
    for game_map in maps:
        d = str(game_map.get("difficulty", ""))
        by_difficulty[d] = by_difficulty.get(d, 0) + 1
    maps_value = (
        f"{len(maps)} loaded — "
        + " · ".join(f"{d} {by_difficulty[d]}"
                     for d in _MAP_DIFFICULTY_ORDER if d in by_difficulty)
        + " (full list: the 🗺️ Maps panel)")
    rounds_value = ", ".join(str(int(r["round"])) for r in default_rounds())
    embed = RenderedEmbed(
        title="🐵 BTD6 Assistant — Diagnostics",
        description="",
        fields=(
            ("Towers", ", ".join(t.canonical for t in dataset.towers()), False),
            ("Heroes", ", ".join(h.canonical for h in dataset.heroes()), False),
            ("Maps", maps_value, False),
            ("Modes",
             ", ".join(str(m.get("canonical", "")) for m in list_modes()),
             False),
            ("Rounds tracked", rounds_value, False),
            ("Data source",
             f"`{DATA_SOURCE_LABEL}` · available: **True**", False),
        ),
        style_token="green")
    return append_ctx(embed, "btd6_diagnostics:catalog")


def test_intent_card(text: str) -> RenderedEmbed:
    from sb.domain.btd6 import resolver

    intent = resolver.resolve(text)
    return RenderedEmbed(
        title="🐵 BTD6 — test-intent",
        description=f"Resolved intent for: ``{text[:200]}``",
        fields=(
            ("Confidence", f"{intent.confidence:.2f}", True),
            ("Towers",
             ", ".join(t.canonical for t in intent.towers) or "—", False),
            ("Heroes",
             ", ".join(h.canonical for h in intent.heroes) or "—", False),
            ("Maps",
             ", ".join(m.canonical for m in intent.maps) or "—", False),
            ("Modes",
             ", ".join(m.canonical for m in intent.modes) or "—", False),
            ("Rounds",
             ", ".join(str(n) for n in intent.candidate_round_numbers) or "—",
             False),
        ),
        style_token="green")


# --- hub (views/btd6/panel.py build_btd6_panel_embed) -------------------------


#: useful-first kinds + emoji, the shipped hub "Currently active" roster.
_HUB_ACTIVE_KINDS = (("race", "🏁"), ("boss", "👑"), ("ct", "🗺️"),
                     ("odyssey", "🌊"), ("event", "🎪"))


def hub_card() -> RenderedEmbed:
    active_lines = "\n".join(
        f"⚪ {emoji} `{kind:<8}` —" for kind, emoji in _HUB_ACTIVE_KINDS)
    embed = RenderedEmbed(
        title="🐵 BTD6 Assistant",
        description=("Ask BTD6 questions or browse tower / hero / round / "
                     "event info by category. Staff can open the **🛠️ Admin** "
                     "panel for manual data fetches and diagnostics."),
        fields=(
            ("📚 Reference (seed)",
             f"Data version: `{data_version()}` · "
             f"Game version: `{dataset.game_version()}`\n"
             f"{len(dataset.towers())} towers • "
             f"{len(dataset.heroes())} heroes • "
             f"{len(list_maps())} maps • "
             f"{len(list_modes())} modes • "
             f"{len(default_rounds())} rounds", False),
            ("🎯 Currently active", active_lines, False),
        ),
        footer=("!btd6 ask <q> · !btd6 tower <n> · !btd6 round <N> · "
                "!btd6 leaderboard <race|boss> · !btd6 status"),
        style_token="green")
    return append_ctx(embed, "btd6_hub:main")


# --- live events / sources / ops (empty-state honest: D-0046 successor) ------


_LIVE_EVENT_SPECS: dict[str, dict[str, str]] = {
    "btd6_race": {"title": "🐵 BTD6 — Races", "noun": "race",
                  "source_key": "nk_btd6_races"},
    "btd6_boss": {"title": "🐵 BTD6 — Bosses", "noun": "boss event",
                  "source_key": "nk_btd6_bosses"},
    "btd6_ct": {"title": "🐵 BTD6 — Contested Territory", "noun": "CT event",
                "source_key": "nk_btd6_ct"},
    "btd6_odyssey": {"title": "🐵 BTD6 — Odysseys", "noun": "odyssey",
                     "source_key": "nk_btd6_odyssey"},
    "btd6_event": {"title": "🐵 BTD6 — Events", "noun": "event",
                   "source_key": "nk_btd6_events"},
}

_EVENT_KIND_TITLE = {
    "btd6_race": "🏁 BTD6 Race",
    "btd6_boss": "👑 BTD6 Boss",
    "btd6_ct": "🗺️ BTD6 Contested Territory",
    "btd6_odyssey": "🌊 BTD6 Odyssey",
    "btd6_event": "🎪 BTD6 Event",
}


def live_events_card(entity_kind: str) -> RenderedEmbed:
    if not entity_kind.startswith("btd6_"):
        entity_kind = f"btd6_{entity_kind}"
    spec = _LIVE_EVENT_SPECS.get(entity_kind)
    if spec is None:
        return RenderedEmbed(
            title="🐵 BTD6 — Unknown kind",
            description=(f"`{entity_kind}` isn't a known live-event kind. "
                         "Try one of: `race`, `boss`, `ct`, `odyssey`, "
                         "`event`."),
            style_token="red")
    short_kind = entity_kind.removeprefix("btd6_") or "event"
    embed = RenderedEmbed(
        title=spec["title"],
        description=(f"No {spec['noun']} facts recorded yet. Try "
                     f"`!btd6 refresh-source {spec['source_key']}` to fetch "
                     "live data."),
        style_token="gold")
    return append_ctx(embed, f"btd6_{short_kind}:list")


def event_detail_card(kind: str, entity_key: str) -> RenderedEmbed:
    norm = kind if kind.startswith("btd6_") else f"btd6_{kind}"
    title = f"{_EVENT_KIND_TITLE.get(norm, norm)} — {entity_key}"
    return RenderedEmbed(
        title=title,
        description=(f"No event found for kind=`{norm}` id=`{entity_key}`. "
                     f"Try `!btd6 live {norm.removeprefix('btd6_')}` to "
                     "list active events of this kind."),
        style_token="red")


def leaderboard_card(kind: str, event_id: str | None = None) -> RenderedEmbed:
    norm = (kind or "").strip().lower()
    if norm not in {"race", "boss"}:
        return RenderedEmbed(
            title="🐵 BTD6 — Leaderboard",
            description=f"Unknown kind `{kind!r}` — use `race` or `boss`.",
            style_token="red")
    refresh_source = "nk_btd6_races" if norm == "race" else "nk_btd6_bosses"
    if not event_id:
        return RenderedEmbed(
            title=f"🐵 BTD6 — {norm.title()} leaderboard",
            description=(f"No active {norm} found. Try `!btd6 refresh-source "
                         f"{refresh_source}` to fetch live data."),
            style_token="gold")
    embed = RenderedEmbed(
        title=f"🐵 BTD6 — {norm.title()} leaderboard — {event_id}",
        description=(f"No leaderboard rows stored for `{event_id}` yet. "
                     f"Try `!btd6 refresh-source {refresh_source}`."),
        footer=("Showing standard solo leaderboard. Elite / team modes are "
                "not yet ingested.") if norm == "boss" else "No rows.",
        style_token="gold")
    return embed


def refresh_source_card(source_key: str) -> RenderedEmbed:
    """The unknown-source result, the shape the shipped ingestion service
    returned for an unregistered key (status=disabled ·
    error=source_not_registered) — with zero sources registered, every key
    takes this leg."""
    return RenderedEmbed(
        title=f"🐵 BTD6 — Refresh '{source_key}'",
        description="",
        fields=(
            (f"`{source_key}`",
             "status=`disabled` · facts=0 · duration=0ms\n"
             "run_id=`—` · error=`source_not_registered`\n"
             "written=0", False),
            ("Known source keys", "—", False),
        ),
        style_token="red")


def source_health_card() -> RenderedEmbed:
    embed = RenderedEmbed(
        title="🐵 BTD6 — Source Health",
        description="No BTD6 sources registered yet.",
        style_token="gold")
    return append_ctx(embed, "btd6_diagnostics:sources")


def latest_data_card() -> RenderedEmbed:
    embed = RenderedEmbed(
        title="🐵 BTD6 — Latest Data",
        description="No facts recorded yet.",
        style_token="gold")
    return append_ctx(embed, "btd6_diagnostics:latest_data")


def readiness_card() -> RenderedEmbed:
    """`!btd6 ops readiness` — the shipped "disabled" verdict. The
    ingestion supervisor is the D-0046 successor port: it does not exist
    in this build, so env-enabled/supervisor-running are honestly ❌ and
    every count below is the true zero (an env flag alone could not turn
    it on — reporting it would mislead)."""
    yn = "❌ no"
    embed = RenderedEmbed(
        title="🐵 BTD6 ingestion readiness — 🚫 disabled",
        description=("Ingestion is **switched off** (`BTD6_INGESTION_ENABLED`"
                     " is not `true`). No scheduled fetches run; the sources "
                     "below are configured but dormant."),
        fields=(
            ("Ingestion", f"env enabled: {yn}\nsupervisor running: ❌ no",
             True),
            ("Sources",
             "total: 0\nenabled: 0\ndisabled: 0\nenabled w/o base_url: 0",
             True),
            ("Freshness (enabled)",
             "🟢 fresh: 0\n🟡 aging: 0\n🔴 stale: 0\n⚪ never: 0", True),
            ("Open circuit breakers", "none", False),
            ("Recent runs", "scanned: 0\nfailures: 0\nlast run: —", False),
        ),
        style_token="greyple")
    return embed


def runs_card(source_key: str | None = None) -> RenderedEmbed:
    scope = f" — {source_key}" if source_key else ""
    return RenderedEmbed(
        title=f"🐵 BTD6 ingestion runs{scope}",
        description=("No ingestion runs recorded yet." if source_key is None
                     else f"No ingestion runs recorded for `{source_key}` "
                          "yet."),
        style_token="blurple")


# --- strategy memory (views/btd6/strategy_browse.py) --------------------------


def _visibility_badge(row: dict) -> str:
    return "📦 published" if row.get("visibility") == "published" else "🛡️ guild"


def _approval_label(row: dict) -> str:
    status = row.get("approval_status", "draft")
    approved_by = row.get("approved_by")
    if approved_by == "ai":
        return f"`{status}` · approved_by=ai"
    if approved_by == "staff":
        return f"`{status}` · approved_by=staff"
    return f"`{status}`"


def _summarize_row(row: dict) -> str:
    badge = _visibility_badge(row)
    approval = _approval_label(row)
    title = row.get("title") or "(untitled)"
    summary = (row.get("summary") or "").strip()
    if len(summary) > 100:
        summary = summary[:99] + "…"
    return f"{badge} · {approval} · **{title}** — {summary}"


async def browse_card(limit: int = 10) -> RenderedEmbed:
    from sb.domain.btd6 import store

    rows = await store.list_strategies(visibility="published",
                                       limit=max(1, min(int(limit), 25)))
    if not rows:
        embed = RenderedEmbed(title="🐵 BTD6 — Published strategies",
                              description="No published strategies yet.",
                              style_token="green")
        return append_ctx(embed, "btd6_strategy:browse")
    embed = RenderedEmbed(
        title="🐵 BTD6 — Published strategies",
        description=(f"Showing {len(rows)} published strategies "
                     "(max 25 per page)."),
        fields=tuple(
            (f"#{row['id']} · {_visibility_badge(row)}",
             _summarize_row(row), False) for row in rows),
        footer=("!btd6 strategy <id> for detail · staff-only commands gate "
                "writes."),
        style_token="green")
    return append_ctx(embed, "btd6_strategy:browse")


async def mine_card(guild_id: int, submitter_id: int,
                    limit: int = 10) -> RenderedEmbed:
    from sb.domain.btd6 import store

    rows = await store.list_strategies(guild_id=guild_id,
                                       submitted_by=submitter_id,
                                       limit=max(1, min(int(limit), 25)))
    if not rows:
        embed = RenderedEmbed(
            title="🐵 BTD6 — My strategy submissions",
            description="You have not submitted any strategies in this guild.",
            style_token="green")
        return append_ctx(embed, "btd6_strategy:mine")
    embed = RenderedEmbed(
        title="🐵 BTD6 — My strategy submissions",
        description=(f"Showing {len(rows)} of your submissions in this guild "
                     "(max 25)."),
        fields=tuple(
            (f"#{row['id']} · {_visibility_badge(row)}",
             _summarize_row(row), False) for row in rows),
        style_token="green")
    return append_ctx(embed, "btd6_strategy:mine")


async def detail_card(strategy_id: int,
                      viewer_guild_id: int | None = None) -> RenderedEmbed | str:
    from sb.domain.btd6 import store

    row = await store.get_strategy(strategy_id)
    if row is None:
        return f"Strategy #{strategy_id} not found."
    visibility = row.get("visibility")
    if visibility != "published" and viewer_guild_id is not None:
        origin = row.get("origin_guild_id")
        current = row.get("current_guild_id")
        if viewer_guild_id not in {origin, current}:
            return (f"Strategy #{strategy_id} is guild-local; it is not "
                    "visible from this guild.")
    fields: list[tuple[str, str, bool]] = [
        ("Visibility", _visibility_badge(row), True),
        ("Approval", _approval_label(row), True),
        ("Version", str(row.get("version") or 1), True),
    ]
    for label, key in (("Map", "map"), ("Mode", "mode"),
                       ("Difficulty", "difficulty"), ("Hero", "hero")):
        if row.get(key):
            fields.append((label, str(row[key]), True))
    embed = RenderedEmbed(
        title=(f"🐵 BTD6 — Strategy #{row['id']}: "
               f"{row.get('title') or '(untitled)'}"),
        description=row.get("summary") or "(no summary)",
        fields=tuple(fields),
        footer=(f"origin_guild={row.get('origin_guild_id') or '—'} · "
                f"current_guild={row.get('current_guild_id') or '—'} · "
                f"submitted_by={row.get('submitted_by') or '—'}"),
        style_token="green")
    return append_ctx(embed, f"btd6_strategy:{row['id']}")


async def audit_card(strategy_id: int) -> RenderedEmbed:
    rows = await _strategy_audit_rows(strategy_id)
    if not rows:
        embed = RenderedEmbed(
            title=f"🐵 BTD6 — Strategy #{strategy_id} audit",
            description=f"No audit rows for strategy #{strategy_id}.",
            style_token="green")
        return append_ctx(embed, f"btd6_strategy:{strategy_id}")
    fields = []
    for r in rows[:25]:
        when = r.get("occurred_at")
        when_str = when.isoformat(timespec="minutes") if when else "—"
        fields.append((
            f"`{r.get('mutation_type')}` · {r.get('actor_type')}",
            f"actor_id=`{r.get('actor_id') or '—'}` · at=`{when_str}`",
            False))
    embed = RenderedEmbed(
        title=f"🐵 BTD6 — Strategy #{strategy_id} audit",
        description=f"Showing {len(rows)} audit row(s).",
        fields=tuple(fields), style_token="green")
    return append_ctx(embed, f"btd6_strategy:{strategy_id}")


async def _strategy_audit_rows(strategy_id: int) -> list[dict]:
    """Per-strategy transitions off the K7 central audit spine (the shipped
    ``btd6_strategy_audit`` table's D-0046 re-home)."""
    try:
        from sb.kernel.db.pool import fetchall

        rows = await fetchall(
            "SELECT mutation_type, actor_id, actor_type, occurred_at, "
            "new_value FROM audit_log WHERE subsystem='btd6' "
            "ORDER BY occurred_at DESC LIMIT 200", ())
    except Exception:  # noqa: BLE001 — diagnostics never crash the view
        return []
    needle = f'"strategy_id": {int(strategy_id)}'
    return [dict(r) for r in rows if needle in str(r.get("new_value") or "")]


async def strategies_payload(guild_id: int) -> str:
    from sb.domain.btd6 import store

    rows = await store.list_strategies(guild_id=guild_id, limit=10)
    if not rows:
        return "No BTD6 strategies recorded for this guild yet."
    lines = []
    for row in rows:
        tag = ("📦 published" if row.get("visibility") == "published"
               else "🛡️ guild")
        lines.append(
            f"{tag} · `{row['approval_status']}` · **{row['title']}** "
            f"— {str(row['summary'])[:80]}")
    return "\n".join(lines)


async def pending_payload(guild_id: int, limit: int = 5) -> str | list[dict]:
    """Rows pending review, or the shipped none-pending string. The shipped
    review buttons (StrategyReviewView) ride `!btd6strat pending`'s existing
    staff view; this surface serves the golden-pinned string + row list."""
    from sb.domain.btd6 import store

    rows = await store.list_strategies(
        guild_id=guild_id, approval_status="pending",
        limit=max(1, min(int(limit), 10)))
    if not rows:
        return "No pending strategies awaiting review for this guild."
    return rows


_RELEVANT_DECISIONS = ("denied", "skipped", "errored", "degraded")


async def why_no_response_payload(guild_id: int,
                                  limit: int = 10) -> RenderedEmbed | str:
    from sb.kernel.ai import decision_audit

    safe_limit = max(1, min(50, int(limit)))
    try:
        rows = [dict(r) if not isinstance(r, dict) else r
                for r in await decision_audit.query(guild_id, limit=safe_limit)]
    except Exception:  # noqa: BLE001 — diagnostics never crash the view
        rows = []
    btd6_rows = [r for r in rows
                 if str(r.get("task", "")) == "btd6.answer"
                 and r.get("decision") in _RELEVANT_DECISIONS]
    if not btd6_rows:
        return "No recent BTD6 denials or skips for this guild."
    fields = []
    for row in btd6_rows[:10]:
        profile_ids = row.get("instruction_profile_ids") or []
        profile_str = ", ".join(str(pid) for pid in profile_ids) or "—"
        fields.append((
            f"`{row['decision']}` · `{row['reason_code']}`",
            (f"channel=<#{row['channel_id']}> · user=<@{row['user_id']}>\n"
             f"route=`{row.get('route') or '—'}` · "
             f"provider=`{row.get('provider') or '—'}` · "
             f"model=`{row.get('model') or '—'}`\n"
             f"policy_snapshot=`{row.get('policy_snapshot_hash') or '—'}` · "
             f"profiles=`{profile_str}`"), False))
    return RenderedEmbed(
        title="🐵 BTD6 — why-no-response",
        description=(f"Most recent BTD6 denials / skips for this guild "
                     f"(showing {min(len(btd6_rows), 10)} of "
                     f"{len(btd6_rows)})."),
        fields=tuple(fields), style_token="gold")


async def grounding_payload(guild_id: int,
                            message_id: int) -> RenderedEmbed | str:
    from sb.kernel.ai import decision_audit

    try:
        rows = [dict(r) if not isinstance(r, dict) else r
                for r in await decision_audit.query(guild_id, limit=200)]
    except Exception:  # noqa: BLE001 — diagnostics never crash the view
        rows = []
    target = next((r for r in rows
                   if int(r.get("message_id") or 0) == int(message_id)), None)
    if target is None:
        return (f"No audit row for message_id={message_id}. The bot may "
                "not have processed that message.")
    profile_ids = target.get("instruction_profile_ids") or []
    return RenderedEmbed(
        title=f"🐵 BTD6 — Grounding for message {message_id}",
        description=(f"Decision: `{target['decision']}` · "
                     f"reason: `{target['reason_code']}` · "
                     f"task: `{target.get('task') or '—'}`"),
        fields=(
            ("Routing",
             f"route=`{target.get('route') or '—'}` · "
             f"provider=`{target.get('provider') or '—'}` · "
             f"model=`{target.get('model') or '—'}`", False),
            ("Policy state",
             f"policy_snapshot=`{target.get('policy_snapshot_hash') or '—'}` "
             f"· profiles=`{', '.join(str(p) for p in profile_ids) or '—'}`",
             False),
        ),
        style_token="gold")

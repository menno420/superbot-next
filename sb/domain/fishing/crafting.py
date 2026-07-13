"""The shared fish-spend planner (band 6, D-0043 slice 2) — the shipped
``services/fishing_workflow.py`` eligibility/spend trio ported verbatim
(oracle menno420/superbot @ cdb26804, ``_eligible_fish`` /
``eligible_fish_total`` / ``_plan_fish_spend``).

Every fish→gear craft (rod recipes now; the bait/charm recipes on the
later rungs) reads the same rule: a recipe consumes ``fish_count`` caught
fish whose ``size_rank`` is ``≤ max_size_rank``, spending the smallest
ranks first (ties broken by name) so the player keeps their bigger
catches. Any recipe-shaped object carrying ``fish_count`` +
``max_size_rank`` plans through here (the shipped ``_FishRecipe``
duck-shape — :class:`sb.domain.fishing.rods.RodRecipe` today).

Pure + stdlib-only over an in-memory inventory dict (no Discord, no DB);
the species size ranks read from ``sb/domain/fishing/catalog.py``."""

from __future__ import annotations

from sb.domain.fishing import catalog

__all__ = [
    "eligible_fish",
    "eligible_fish_total",
    "plan_fish_spend",
]


def eligible_fish(inventory: dict[str, int],
                  recipe) -> list[tuple[int, str, int]]:
    """The player's fish eligible toward *recipe*, as ``(size_rank, name, have)``.

    Eligible = a known fish species whose ``size_rank`` is ``≤ recipe.max_size_rank``.
    Shared by :func:`plan_fish_spend` (which fish to debit) and
    :func:`eligible_fish_total` (live progress display) so both read the exact
    same eligibility rule.
    """
    eligible: list[tuple[int, str, int]] = []  # (size_rank, name, have)
    for name, have in inventory.items():
        if have <= 0:
            continue
        species = catalog.species_by_name(name)
        if species is None or species.size_rank > recipe.max_size_rank:
            continue
        eligible.append((species.size_rank, name, have))
    return eligible


def eligible_fish_total(inventory: dict[str, int], recipe) -> int:
    """Total fish in *inventory* eligible toward *recipe* (size_rank ≤ cap).

    A pure progress readout — unlike :func:`plan_fish_spend` it never gates on
    ``recipe.fish_count`` being met, so a caller can show "7/10 eligible fish"
    before the player has enough to craft.
    """
    return sum(have for _, _, have in eligible_fish(inventory, recipe))


def plan_fish_spend(inventory: dict[str, int],
                    recipe) -> dict[str, int] | None:
    """Choose which eligible fish to consume for *recipe* (smallest-first).

    Consumes the smallest ranks first (ties broken by name) so the player keeps
    their bigger catches. Returns a ``{fish_name: count}`` spend map, or ``None``
    when the player lacks ``recipe.fish_count`` eligible fish.
    """
    eligible = eligible_fish(inventory, recipe)
    if sum(have for _, _, have in eligible) < recipe.fish_count:
        return None

    eligible.sort(key=lambda e: (e[0], e[1]))  # smallest size, then name
    spend: dict[str, int] = {}
    remaining = recipe.fish_count
    for _, name, have in eligible:
        if remaining <= 0:
            break
        take = min(have, remaining)
        spend[name] = take
        remaining -= take
    return spend

"""Mining structure/gear recipes (band 6, slice 4) — the shipped craft table,
ported from the oracle ``disbot/utils/mining/recipes.py`` + its shipped
``data/json/recipes.json``.

The oracle loaded recipes from a JSON data file with a hard-coded fallback; the
target ships no ``data/json`` tree, so the shipped ``recipes.json`` contents are
inlined here as the in-code source of truth (``_SHIPPED_RECIPES``) and
``load_recipes`` returns a normalised copy — the same ``{recipe: {material:
qty}}`` mapping the oracle's loader produced (keys lower-cased, int quantities).

Consumed by the quick-craft write lane (``sb/domain/mining/ops.py``
``record_quick_craft``): re-craft the last gear item that broke from its recipe.
NO golden drives a craft write — every imported sweep pinned the bare guard/read
byte (goldens/mining/sweep_quickcraft.json pins the fresh-player "Nothing has
broken recently …" read off the store's NULL ``last_broken_item``), so this
table is faithful-port scaffolding, not a parity surface.
"""

from __future__ import annotations

#: The shipped recipe table (disbot/data/json/recipes.json, verbatim). Product
#: name → the raw materials (and counts) its craft consumes. Starter gear is
#: craftable from mineable resources so broken gear (the durability sink) is
#: always re-craftable, not buy-only.
_SHIPPED_RECIPES: dict[str, dict[str, int]] = {
    "pickaxe": {"wood": 2, "stone": 3},
    "iron pickaxe": {"iron": 3, "wood": 2},
    "torch": {"wood": 2},
    "lantern": {"iron": 2, "gold": 1},
    "sword": {"wood": 1, "stone": 2},
    "iron sword": {"iron": 2, "wood": 1},
    "shield": {"wood": 6, "iron": 1},
    "stone hut": {"stone": 5},
    "wooden house": {"wood": 8},
    "gold statue": {"gold": 4},
    "diamond throne": {"diamond": 6},
    "giant fortress": {"stone": 50, "wood": 30, "iron": 10},
    "gold pickaxe": {"gold": 4, "wood": 2},
    "diamond pickaxe": {"diamond": 3, "gold": 1, "wood": 2},
    "diamond lantern": {"diamond": 2, "iron": 2},
    "diamond sword": {"diamond": 2, "wood": 1},
    "bronze sword": {"bronze": 2, "wood": 1},
    "silver sword": {"silver": 2, "wood": 1},
    "gold sword": {"gold": 2, "wood": 1},
    "bronze shield": {"bronze": 2, "wood": 2},
    "iron shield": {"iron": 2, "wood": 2},
    "silver shield": {"silver": 2, "wood": 2},
    "gold shield": {"gold": 2, "wood": 2},
    "diamond shield": {"diamond": 2, "wood": 2},
    "bronze helmet": {"bronze": 3},
    "iron helmet": {"iron": 3},
    "silver helmet": {"silver": 3},
    "gold helmet": {"gold": 3},
    "diamond helmet": {"diamond": 3},
    "bronze chestplate": {"bronze": 5},
    "iron chestplate": {"iron": 5},
    "silver chestplate": {"silver": 5},
    "gold chestplate": {"gold": 5},
    "diamond chestplate": {"diamond": 5},
    "bronze leggings": {"bronze": 4},
    "iron leggings": {"iron": 4},
    "silver leggings": {"silver": 4},
    "gold leggings": {"gold": 4},
    "diamond leggings": {"diamond": 4},
    "bronze boots": {"bronze": 2},
    "iron boots": {"iron": 2},
    "silver boots": {"silver": 2},
    "gold boots": {"gold": 2},
    "diamond boots": {"diamond": 2},
}


def load_recipes() -> dict[str, dict[str, int]]:
    """The recipe table — recipe names + material names lower-cased, int
    quantities (the oracle loader's normalisation, over the inlined shipped
    source). A fresh dict each call (the oracle returned a copy)."""
    return {name.lower(): {mat.lower(): int(qty) for mat, qty in reqs.items()}
            for name, reqs in _SHIPPED_RECIPES.items()}


__all__ = ["load_recipes"]

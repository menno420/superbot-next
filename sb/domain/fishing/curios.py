"""Fishing curios — cosmetic carvings crafted from coral (the second rare
drop), ported verbatim from the oracle ``disbot/utils/fishing/curios.py``.

The fishing rare-material pattern's *second* instance: the **pearl**
(:data:`sb.domain.fishing.ops.PEARL_ITEM`) sinks into a *bait*; **coral**
(:data:`sb.domain.fishing.ops.CORAL_ITEM`, a deepwater-only reef drop)
sinks into a *cosmetic collection* — carved "curios". A curio is a
purely-cosmetic collectible stored in the shared ``mining_inventory``
(no migration; the existing inventory browser shows it). The value is
the *collection* — a completionist goal like the Fishdex — and a
perpetual home for coral.

Pure + stdlib-only (no store / db): the ``fishing.craft_curio`` op owns
the craft write (debit coral, grant the curio in one txn); the handlers
read this catalog. Mirrors the bait module's recipe helpers exactly.

ONE sanctioned rename (the slice-3 ``bait_effect_text`` precedent): the
shipped ``craftable_key_for`` lands as :func:`curio_craftable_key_for`
because ``sb/domain/fishing/bait.py`` already exports the package's
``craftable_key_for`` (check_symbol_shadowing rule 2 — public names are
package-unique). Behaviour and produced bytes are identical.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Curio:
    """One carved curio — a cosmetic collectible crafted from coral.

    ``item`` is the stable ``mining_inventory`` key (also the display
    name, kept lower-cased to match how inventory keys are stored);
    ``coral_cost`` coral are consumed to carve one. Rarer curios cost
    more coral — the collection's long-tail. Purely cosmetic: no
    gameplay effect, never sold.
    """

    key: str  # stable lookup key (also the inventory item key)
    item: str  # the mining_inventory item name (== key; explicit for clarity)
    name: str  # display name
    emoji: str
    coral_cost: int
    rarity: str  # display rarity (Uncommon / Rare / Epic) — cosmetic only


#: The curio shelf, cheapest first (shipped verbatim — the ascending coral
#: cost makes the top curio a genuine deep-sea trophy;
#: goldens/fishing/sweep_curios pins every rendered byte).
CURIO_CATALOG: tuple[Curio, ...] = (
    Curio(
        "coral shell",
        "coral shell",
        "Carved Coral Shell",
        "🐚",
        coral_cost=2,
        rarity="Uncommon",
    ),
    Curio(
        "coral seahorse",
        "coral seahorse",
        "Coral Seahorse",
        "🌊",
        coral_cost=4,
        rarity="Rare",
    ),
    Curio("coral idol", "coral idol", "Coral Idol", "🗿", coral_cost=8,
          rarity="Epic"),
    Curio(
        "coral leviathan",
        "coral leviathan",
        "Coral Leviathan",
        "🐉",
        coral_cost=16,
        rarity="Legendary",
    ),
)

_BY_KEY: dict[str, Curio] = {c.key: c for c in CURIO_CATALOG}

#: The stable keys, in shelf order (for selects / validation).
CURIO_KEYS: tuple[str, ...] = tuple(c.key for c in CURIO_CATALOG)

#: The inventory item names every curio occupies — used to tally a
#: player's collection without re-deriving it at each call site.
CURIO_ITEMS: tuple[str, ...] = tuple(c.item for c in CURIO_CATALOG)


def curio_by_key(key: str | None) -> Curio | None:
    """The :class:`Curio` for *key*, or ``None`` for an unknown / empty
    key."""
    if not key:
        return None
    return _BY_KEY.get(key)


def cost_text(curio: Curio) -> str:
    """A short human label of a curio's cost, e.g. ``4 🪸 coral``."""
    return f"{curio.coral_cost} 🪸 coral"


def curio_craftable_key_for(text: str | None) -> str | None:
    """Resolve typed *text* (a key or a display name) to a curio key
    (the shipped ``craftable_key_for``, renamed — see the module
    docstring).

    Case-insensitive; matches either the stable key (``coral idol``) or
    the display name (``Coral Idol``). Returns ``None`` for empty input
    or an unrecognised curio.
    """
    if not text:
        return None
    needle = text.strip().lower()
    for key in CURIO_KEYS:
        curio = _BY_KEY.get(key)
        if curio is None:
            continue
        if needle in (key.lower(), curio.name.lower()):
            return key
    return None


def collection_progress(inventory: dict[str, int]) -> tuple[int, int]:
    """``(owned, total)`` — how many distinct curios *inventory* holds
    vs. the set.

    A curio is "owned" when its item key is present with a positive
    quantity. Pure over an ``{item: qty}`` map; the handler renders the
    count.
    """
    owned = sum(1 for item in CURIO_ITEMS if inventory.get(item, 0) > 0)
    return owned, len(CURIO_ITEMS)


__all__ = [
    "Curio",
    "CURIO_CATALOG",
    "CURIO_KEYS",
    "CURIO_ITEMS",
    "curio_by_key",
    "cost_text",
    "curio_craftable_key_for",
    "collection_progress",
]

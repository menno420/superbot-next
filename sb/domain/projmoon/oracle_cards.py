"""Project Moon oracle-surface CARDS (band 7) — the shipped ``!pm`` reply
embeds, byte-for-byte.

Every builder here is a focused port of the shipped formatter that
produced the goldens/project_moon corpus (oracle @7f7628e1):

* ``views/projmoon/browse.py`` — the overview / kind-list / entry /
  origins embeds (GAME_COLOR purple, the verify-at-ingest provenance
  footer);
* ``cogs/project_moon_cog.py`` — the two greyple miss cards (the bare
  ``discord.Embed`` sends of ``pm_lookup`` / ``_category_lookup``, which
  carry NO footer — the shipped asymmetry the goldens pin).

Builders return :class:`~sb.kernel.panels.render.RenderedEmbed` —
presentation-free and side-effect-free; the handlers in
:mod:`sb.domain.projmoon.service` own the sends. Shipped quirks are
preserved verbatim: the ``rstrip("s")`` singularizer ("No statuse
matches …") and the ``!pm list <entity_kind>`` hint that names the
internal kind key ("damage_type") — parity pins ORACLE semantics, never
what current taste would write.
"""

from __future__ import annotations

from sb.domain.projmoon import dataset
from sb.kernel.panels.render import RenderedEmbed

__all__ = [
    "FOOTER",
    "category_miss_card",
    "entry_card",
    "kind_card",
    "lookup_miss_card",
    "origins_card",
    "overview_card",
]

#: the shipped provenance footer (views/projmoon/browse.py _FOOTER), verbatim.
FOOTER = "Project Moon · Limbus Company — summarized facts (verify-at-ingest)"

#: GAME_COLOR (utils/ui_constants.py) — discord.Color.purple().
_PURPLE = "purple"
#: discord.Color.greyple() — the two miss cards.
_GREYPLE = "greyple"


def overview_card() -> RenderedEmbed:
    """The browse landing card (build_overview_embed): what this domain
    knows, with counts — 6 names per kind, then ", …"."""
    fields: list[tuple[str, str, bool]] = []
    for kind in dataset.entity_kinds():
        entries = dataset.get_entries(kind)
        names = ", ".join(e.canonical for e in entries[:6])
        if len(entries) > 6:
            names += ", …"
        fields.append((f"{dataset.KIND_LABELS[kind]} ({len(entries)})",
                       names or "—", False))
    return RenderedEmbed(
        title="🌑 Project Moon — Limbus knowledge",
        description=(
            "A browsable reference for *Limbus Company*. Pick a category "
            "below, or use `!pm <category> <name>` (e.g. `!pm mechanic "
            "clash`, `!pm status sinking`) or `!pm lookup <anything>`."
        ),
        fields=tuple(fields),
        footer=FOOTER,
        style_token=_PURPLE)


def kind_card(kind: str) -> RenderedEmbed:
    """One entity kind, every entry in file order (build_kind_embed) —
    a ``color`` / ``category`` extra renders as a name suffix."""
    fields: list[tuple[str, str, bool]] = []
    for entry in dataset.get_entries(kind):
        suffix = ""
        if "color" in entry.extra:
            suffix = f" — {entry.extra['color']}"
        elif "category" in entry.extra:
            suffix = f" — {entry.extra['category']}"
        fields.append((f"{entry.canonical}{suffix}", entry.description,
                       False))
    return RenderedEmbed(
        title=f"🌑 Limbus — {dataset.KIND_LABELS[kind]}",
        description="",
        fields=tuple(fields),
        footer=FOOTER,
        style_token=_PURPLE)


def entry_card(entry: dataset.LimbusEntry) -> RenderedEmbed:
    """A single Limbus fact with its kind label + extras
    (build_entry_embed)."""
    fields: list[tuple[str, str, bool]] = [
        ("Category", dataset.KIND_LABELS[entry.entity_kind], True),
    ]
    if "category" in entry.extra:
        fields.append(("Group", str(entry.extra["category"]), True))
    if "color" in entry.extra:
        fields.append(("Affinity colour", str(entry.extra["color"]), True))
    if "rank" in entry.extra:
        fields.append(("Grade rank", f"{entry.extra['rank']} of 5", True))
    origin = entry.extra.get("literary_origin")
    if isinstance(origin, dict) and origin.get("work") and origin.get("author"):
        fields.append(("Literary origin",
                       f"*{origin['work']}* — {origin['author']}", False))
    if entry.aliases:
        fields.append(("Also known as", ", ".join(entry.aliases), False))
    return RenderedEmbed(
        title=f"🌑 {entry.canonical}",
        description=entry.description,
        fields=tuple(fields),
        footer=FOOTER,
        style_token=_PURPLE)


def origins_card() -> RenderedEmbed:
    """Every Sinner ↔ the literary work it is drawn from
    (build_origins_embed)."""
    lines = [f"**{o.canonical}** — *{o.work}*, {o.author}"
             for o in dataset.sinner_origins()]
    return RenderedEmbed(
        title="🌑 Limbus — Sinner literary origins",
        description=("Each of the 12 Sinners is drawn from a work of "
                     "world literature.\n\n" + "\n".join(lines)),
        footer=FOOTER,
        style_token=_PURPLE)


def lookup_miss_card(query: str) -> RenderedEmbed:
    """The ``!pm lookup`` miss (pm_lookup's bare Embed — greyple, NO
    footer; empty query renders the shipped em-dash)."""
    return RenderedEmbed(
        title="🌑 Limbus lookup",
        description=(
            f"I don't have a Limbus entry matching "
            f"**{query.strip() or '—'}**. Try `!pm` to browse what I know."
        ),
        style_token=_GREYPLE)


def category_miss_card(kind: str, name: str) -> RenderedEmbed:
    """The per-category miss (_category_lookup's bare Embed — greyple, NO
    footer; the shipped ``rstrip("s")`` singularizer and the internal
    kind-key hint, verbatim)."""
    label = dataset.KIND_LABELS[kind]
    return RenderedEmbed(
        title=f"🌑 Limbus — {label}",
        description=(
            f"No {label.rstrip('s').lower()} matches **{name.strip()}**. "
            f"Try `!pm list {kind}` to see them all."
        ),
        style_token=_GREYPLE)

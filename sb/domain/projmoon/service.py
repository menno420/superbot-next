"""Project Moon oracle-surface handlers (band 7) — the shipped ``!pm``
read-only browse + lookup tree (oracle ``cogs/project_moon_cog.py``
@7f7628e1), routed over the card builders in
:mod:`sb.domain.projmoon.oracle_cards` (no writes, no DB, no provider
calls — the shipped ``btd6_reference`` posture).

Registered at MODULE IMPORT (declaring IS reserving — the BUG A rule,
sb/domain/role/handlers.py pattern): the live root imports and
dispatches without ever running the manifest ENSURE_REFS hooks.

Shipped semantics preserved:

* every reply is an embed, presented through the ``projmoon.card``
  panel (the shipped ``ctx.send(embed=…)`` — public channel message on
  the prefix surface);
* ``!pm list`` with an unknown/missing category re-opens the browse
  panel (the shipped ``pm_list`` fallback — goldens/project_moon/
  sweep_pm_list pins the panel bytes);
* the two miss cards are greyple and footer-less (the cog's bare
  ``discord.Embed`` sends), while every hit/list card carries the
  provenance footer (views/projmoon/browse.py).
"""

from __future__ import annotations

import dataclasses

from sb.kernel.interaction.handler_kit import Reply

__all__ = ["Reply", "ensure_handler_refs"]


def _query(req) -> str:
    argv = [str(a) for a in tuple(req.args.get("argv", ()) or ())]
    return " ".join(argv).strip() or str(req.args.get("name") or "").strip()


async def _card(req, embed) -> None:
    """Present one oracle card as the shipped public embed reply."""
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef("projmoon.card"),
                     dataclasses.replace(
                         req, args={**dict(req.args), "_card": embed}))


async def _open_hub(req) -> None:
    """The shipped browse-panel fallback (LimbusBrowseView +
    build_overview_embed)."""
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef("projmoon.hub"), req)


async def overview_view(req) -> None:
    """The hub's Overview button — the shipped landing embed."""
    from sb.domain.projmoon import oracle_cards as cards

    await _card(req, cards.overview_card())
    return None


async def lookup_view(req) -> None:
    """``!pm lookup`` — resolve any Limbus name/term across every
    category (shipped pm_lookup)."""
    from sb.domain.projmoon import dataset, oracle_cards as cards

    query = _query(req)
    entry = dataset.resolve(query) if query.strip() else None
    if entry is None:
        await _card(req, cards.lookup_miss_card(query))
        return None
    await _card(req, cards.entry_card(entry))
    return None


# Subcommand name -> entity kind (shipped _KIND_ALIASES, verbatim).
_KIND_ALIASES: dict[str, str] = {
    "sinner": "sinner", "sinners": "sinner",
    "sin": "sin", "sins": "sin",
    "damage": "damage_type", "damagetype": "damage_type",
    "ego": "ego_grade", "grade": "ego_grade",
    "mechanic": "mechanic", "mechanics": "mechanic", "combat": "mechanic",
    "status": "status", "statuses": "status", "keyword": "status",
}


async def list_view(req) -> None:
    """``!pm list <category>`` — a whole category, or the browse panel
    on an unknown category (shipped pm_list)."""
    from sb.domain.projmoon import oracle_cards as cards

    kind = _KIND_ALIASES.get(_query(req).strip().lower())
    if kind is None:
        await _open_hub(req)
        return None
    await _card(req, cards.kind_card(kind))
    return None


async def origins_view(req) -> None:
    """``!pm origins`` — every Sinner ↔ its literary source (shipped
    pm_origins)."""
    from sb.domain.projmoon import oracle_cards as cards

    await _card(req, cards.origins_card())
    return None


def _category_view(kind: str):
    """The shipped _category_lookup: no name = the kind list; a hit =
    the entry card; a miss = the greyple footer-less miss card."""
    async def view(req) -> None:
        from sb.domain.projmoon import dataset, oracle_cards as cards

        name = _query(req)
        if not name.strip():
            await _card(req, cards.kind_card(kind))
            return None
        entry = dataset.resolve(name, kind=kind)
        if entry is None:
            await _card(req, cards.category_miss_card(kind, name))
            return None
        await _card(req, cards.entry_card(entry))
        return None
    return view


sinner_view = _category_view("sinner")
sin_view = _category_view("sin")
status_view = _category_view("status")
ego_view = _category_view("ego_grade")
damage_view = _category_view("damage_type")
mechanic_view = _category_view("mechanic")


_HANDLERS = (
    ("projmoon.overview_view", overview_view),
    ("projmoon.lookup_view", lookup_view),
    ("projmoon.list_view", list_view),
    ("projmoon.origins_view", origins_view),
    ("projmoon.sinner_view", sinner_view),
    ("projmoon.sin_view", sin_view),
    ("projmoon.status_view", status_view),
    ("projmoon.ego_view", ego_view),
    ("projmoon.damage_view", damage_view),
    ("projmoon.mechanic_view", mechanic_view),
)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


def ensure_handler_refs() -> None:
    _register()


_register()

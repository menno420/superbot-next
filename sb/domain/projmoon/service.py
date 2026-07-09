"""Project Moon (Limbus) handlers (band 7) — the shipped ``!pm``
read-only browse + lookup surface over the committed fixtures (no
writes, no DB, no provider calls — the shipped ``btd6_reference``
posture)."""

from __future__ import annotations

from dataclasses import dataclass

from sb.spec.outcomes import SUCCESS

__all__ = ["Reply", "ensure_handler_refs"]


@dataclass(frozen=True)
class Reply:
    outcome: str
    user_message: str


def _ok(text: str) -> Reply:
    return Reply(SUCCESS, text)


def _query(req) -> str:
    argv = [str(a) for a in tuple(req.args.get("argv", ()) or ())]
    return " ".join(argv).strip() or str(req.args.get("name") or "").strip()


def _entry_text(entry) -> str:
    from sb.domain.projmoon import context, dataset

    kind_label = dataset.KIND_LABELS.get(entry.entity_kind, entry.entity_kind)
    return f"**{entry.canonical}** ({kind_label})\n{context._body(entry)}"  # noqa: SLF001


def _kind_text(kind: str) -> str:
    from sb.domain.projmoon import dataset

    label = dataset.KIND_LABELS.get(kind, kind)
    entries = dataset.get_entries(kind)
    lines = [f"**{label}** ({len(entries)}):"]
    for entry in entries:
        lines.append(f"- **{entry.canonical}** — {entry.description[:96]}")
    return "\n".join(lines)


async def overview_view(req) -> Reply:
    from sb.domain.projmoon import dataset

    lines = ["🌑 **Project Moon (Limbus Company) reference** — committed "
             "structural facts:"]
    for kind in dataset.entity_kinds():
        label = dataset.KIND_LABELS.get(kind, kind)
        lines.append(f"- {label}: {len(dataset.get_entries(kind))}")
    lines.append("`!pm lookup <name>` resolves any Limbus term; "
                 "`!pm list <category>` lists a whole category.")
    return _ok("\n".join(lines))


async def lookup_view(req) -> Reply:
    from sb.domain.projmoon import dataset

    query = _query(req)
    entry = dataset.resolve(query) if query else None
    if entry is None:
        return _ok(
            f"🌑 I don't have a Limbus entry matching "
            f"**{query or '—'}**. Try `!pm` to browse what I know.")
    return _ok(_entry_text(entry))


_KIND_ALIASES: dict[str, str] = {
    "sinner": "sinner", "sinners": "sinner",
    "sin": "sin", "sins": "sin",
    "damage": "damage_type", "damagetype": "damage_type",
    "ego": "ego_grade", "grade": "ego_grade",
    "mechanic": "mechanic", "mechanics": "mechanic", "combat": "mechanic",
    "status": "status", "statuses": "status", "keyword": "status",
}


async def list_view(req) -> Reply:
    kind = _KIND_ALIASES.get(_query(req).lower())
    if kind is None:
        return await overview_view(req)
    return _ok(_kind_text(kind))


async def origins_view(req) -> Reply:
    from sb.domain.projmoon import dataset

    lines = ["📖 **Sinner literary origins:**"]
    for origin in dataset.sinner_origins():
        lines.append(f"- **{origin.canonical}** — {origin.work} by {origin.author}")
    return _ok("\n".join(lines))


def _category_view(kind: str):
    async def view(req) -> Reply:
        from sb.domain.projmoon import dataset

        name = _query(req)
        if not name:
            return _ok(_kind_text(kind))
        entry = dataset.resolve(name, kind=kind)
        if entry is None:
            label = dataset.KIND_LABELS.get(kind, kind)
            return _ok(f"🌑 No {label} entry matches **{name}**.")
        return _ok(_entry_text(entry))
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


def ensure_handler_refs() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)

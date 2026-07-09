"""PROJMOON subsystem manifest (band 7, knowledge-domain family) — the
shipped ``!pm`` read-only surface (group aliases limbus/projectmoon;
lookup/list/origins + the six per-category lookups, shipped aliases
verbatim), the projmoon.hub browse panel, and the K10 registrations
(projmoon.answer claimed byte-identical; route probe AFTER btd6;
names-only grounding verifier; MINTED 12-probe A-17 eval suite — the
oracle had no projmoon corpus, A-17(d) mandates one at this band).

The shared VIDEO tasks (video.describe/compare/qa — sb/domain/media)
register here too: media has no command surface of its own, and
projmoon is the band-7 slice that lands it (the AI surface slice wires
the shell; D-0047)."""

from __future__ import annotations

from sb.domain.media import ai_tasks as _media_ai
from sb.domain.projmoon import ai_tasks as _ai_tasks
from sb.domain.projmoon import panels as _panels
from sb.domain.projmoon import service as _service
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef


def _sub(name: str, ref: str, summary: str,
         aliases: tuple[str, ...] = ()) -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX, group="pm",
                       aliases=aliases, route=HandlerRef(ref),
                       audience_tier="user", capability="projmoon",
                       summary=summary, usage=f"!pm {name}")


MANIFEST = SubsystemManifest(
    key="projmoon",
    version=1,
    commands=(
        CommandSpec(name="pm", kind=CommandKind.PREFIX,
                    aliases=("limbus", "projectmoon"),
                    route=HandlerRef("projmoon.overview_view"),
                    audience_tier="user", capability="projmoon",
                    summary="Browse the Project Moon (Limbus) reference.",
                    usage="!pm"),
        _sub("lookup", "projmoon.lookup_view",
             "Resolve any Limbus name/term across every category.",
             aliases=("search", "what")),
        _sub("list", "projmoon.list_view",
             "List a whole category (sinners/sins/damage/ego/statuses)."),
        _sub("origins", "projmoon.origins_view",
             "The 12 Sinners' literary origins.",
             aliases=("origin", "literary")),
        _sub("sinner", "projmoon.sinner_view",
             "Look up one Sinner (or list all).", aliases=("sinners",)),
        _sub("sin", "projmoon.sin_view",
             "Look up one Sin affinity (or list all).",
             aliases=("sins", "affinity")),
        _sub("status", "projmoon.status_view",
             "Look up one status keyword (or list all).",
             aliases=("statuses", "keyword")),
        _sub("ego", "projmoon.ego_view",
             "Look up one E.G.O grade (or list all).", aliases=("grade",)),
        _sub("damage", "projmoon.damage_view",
             "Look up one damage type (or list all).",
             aliases=("damagetype",)),
        _sub("mechanic", "projmoon.mechanic_view",
             "Look up one combat mechanic (or list all).",
             aliases=("mechanics", "combat")),
    ),
    panels=(_panels.projmoon_hub_spec(),),
    settings=(),
    stores=(),
    events=(),
    capabilities=(),
)

_ai_tasks.register_projmoon_ai()
_media_ai.register_video_ai()


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _service.ensure_handler_refs()
    _ai_tasks.register_projmoon_ai()
    _media_ai.register_video_ai()


ENSURE_REFS = _ensure_refs

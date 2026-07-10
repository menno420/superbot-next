"""GENERAL subsystem manifest (band 6) — the shipped fun/info panel
(disbot/cogs/general_cog.py): ``!generalmenu`` (alias ``gmenu``) opens the
shipped ``GeneralMenuView`` overview. The panel's button actions route to
thin read handlers over the content pools (sb/domain/general/content.py);
the sibling shipped prefix commands (!fact, !joke, !quote, !trivia,
!motivate, !eightball, !greet) join when their entry points port — the
subsystem's single golden drives the menu entry point only.
"""

from __future__ import annotations

from sb.domain.general import handlers as _handlers
from sb.domain.general import panels as _panels
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef

MANIFEST = SubsystemManifest(
    key="general",
    version=1,
    commands=(
        CommandSpec(name="generalmenu", kind=CommandKind.PREFIX,
                    route=HandlerRef("general.menu_view"),
                    aliases=("gmenu",),
                    audience_tier="user", capability="general",
                    summary="Open the General menu (facts, jokes, quotes, "
                            "trivia, motivation, 8-ball, greetings).",
                    usage="!generalmenu"),
    ),
    panels=(_panels.general_menu_spec(),),
    settings=(),
    stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs

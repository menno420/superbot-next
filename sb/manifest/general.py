"""GENERAL subsystem manifest (band 6) — the shipped fun/info surface
(disbot/cogs/general_cog.py): ``!generalmenu`` (alias ``gmenu``) opens the
shipped ``GeneralMenuView`` overview, and the seven sibling prefix commands
(!fact, !joke, !quote, !trivia, !motivate, !eightball [8ball], !greet) send
the shipped per-command result embeds (goldens/general/sweep_fact ..
sweep_trivia pin the bytes).

XP-byte note (the goldens' 15/16 vs the menu golden's 25): the shipped
listener awarded chat XP on EVERY human message, commands included, with
``random.randint(xp_min, xp_max)`` on the SAME module-global stream the
command bodies drew their ``random.choice`` picks from — and the command
ran FIRST (process_commands before the XP stage). Under the runner's
per-case seed 42, a no-draw command (!generalmenu) leaves randint(15,25)
as the FIRST draw (=25), while each content command consumes ONE choice
draw first, shifting the award to 16 (len-25 pools) or 15 (len-5/len-8
pools). The port reproduces this by draw ORDER (dispatch before
handle_chat_award — sb/adapters/discord/message_feed.py and the parity
boot's send_command both run that order), never by touching the frozen
chat-award formula.
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
        # the shipped sibling prefix commands (general_cog.py; aliases per
        # the shipped decorators — only eightball carried one).
        CommandSpec(name="fact", kind=CommandKind.PREFIX,
                    route=HandlerRef("general.fact_cmd"),
                    audience_tier="user", capability="general",
                    summary="Sends a random interesting fact.",
                    usage="!fact"),
        CommandSpec(name="joke", kind=CommandKind.PREFIX,
                    route=HandlerRef("general.joke_cmd"),
                    audience_tier="user", capability="general",
                    summary="Sends a random joke.",
                    usage="!joke"),
        CommandSpec(name="quote", kind=CommandKind.PREFIX,
                    route=HandlerRef("general.quote_cmd"),
                    audience_tier="user", capability="general",
                    summary="Sends a random famous quote.",
                    usage="!quote"),
        CommandSpec(name="trivia", kind=CommandKind.PREFIX,
                    route=HandlerRef("general.trivia_cmd"),
                    audience_tier="user", capability="general",
                    summary="Asks a trivia question with a reveal button.",
                    usage="!trivia"),
        CommandSpec(name="motivate", kind=CommandKind.PREFIX,
                    route=HandlerRef("general.motivate_cmd"),
                    audience_tier="user", capability="general",
                    summary="Sends a motivational message.",
                    usage="!motivate"),
        CommandSpec(name="eightball", kind=CommandKind.PREFIX,
                    route=HandlerRef("general.eightball_cmd"),
                    aliases=("8ball",),
                    audience_tier="user", capability="general",
                    summary="Ask the Magic 8-Ball a yes/no question.",
                    usage="!eightball <question>"),
        CommandSpec(name="greet", kind=CommandKind.PREFIX,
                    route=HandlerRef("general.greet_cmd"),
                    audience_tier="user", capability="general",
                    summary="Greets you with a random greeting.",
                    usage="!greet"),
    ),
    panels=(_panels.general_menu_spec(), _panels.card_spec(),
            _panels.trivia_card_spec()),
    settings=(),
    stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs

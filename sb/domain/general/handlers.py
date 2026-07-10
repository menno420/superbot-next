"""General read handlers — thin HandlerRef routes over the content pools
(the shipped general_cog.py button actions: random.choice over the
general_content.json pools). All read-only: no ops, no writes.
"""

from __future__ import annotations

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import SUCCESS

__all__ = ["Reply", "ensure_handler_refs"]


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("general.menu_view")):
        return

    @handler("general.menu_view")
    async def menu_view(req):
        """!generalmenu (alias !gmenu) — the shipped General overview panel
        (GeneralMenuView; parity/goldens/general/sweep_generalmenu.json)."""
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef("general.menu"), req)
        return None

    @handler("general.fact_view")
    async def fact_view(req) -> Reply:
        from sb.domain.general.content import FACTS, pick

        return Reply(SUCCESS, f"💡 {pick(FACTS, 'facts')}")

    @handler("general.joke_view")
    async def joke_view(req) -> Reply:
        from sb.domain.general.content import JOKES, pick

        return Reply(SUCCESS, f"😄 {pick(JOKES, 'jokes')}")

    @handler("general.quote_view")
    async def quote_view(req) -> Reply:
        from sb.domain.general.content import QUOTES, pick

        return Reply(SUCCESS, f"💬 {pick(QUOTES, 'quotes')}")

    @handler("general.trivia_view")
    async def trivia_view(req) -> Reply:
        """The shipped `question || answer` entries; the answer renders as
        a spoiler (the "with reveal" affordance in the panel grammar)."""
        from sb.domain.general.content import TRIVIA, pick

        entry = pick(TRIVIA, "trivia questions")
        question, sep, answer = entry.partition("||")
        if not sep:
            return Reply(SUCCESS, f"🧠 {entry.strip()}")
        return Reply(
            SUCCESS,
            f"🧠 {question.strip()}\n**Answer:** ||{answer.strip()}||")

    @handler("general.motivate_view")
    async def motivate_view(req) -> Reply:
        from sb.domain.general.content import MOTIVATIONS, pick

        return Reply(SUCCESS, pick(MOTIVATIONS, "motivational messages"))

    @handler("general.greet_view")
    async def greet_view(req) -> Reply:
        from sb.domain.general.content import GREETINGS, pick

        return Reply(SUCCESS, pick(GREETINGS, "greetings"))

    @handler("general.eightball_answer")
    async def eightball_answer(req) -> Reply:
        """8-Ball modal submit (args['question'] — the G-10 field_id)."""
        from sb.domain.general.content import EIGHTBALL, pick

        question = str(req.args.get("question", "") or "").strip()
        answer = pick(EIGHTBALL, "8-ball answers")
        if question:
            return Reply(SUCCESS, f"🎱 *{question}*\n{answer}")
        return Reply(SUCCESS, f"🎱 {answer}")


_register()


def ensure_handler_refs() -> None:
    _register()

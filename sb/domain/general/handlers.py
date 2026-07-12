"""General read handlers — thin HandlerRef routes over the content pools
(the shipped general_cog.py button actions: random.choice over the
general_content.json pools). All read-only: no ops, no writes.
"""

from __future__ import annotations

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

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

    # --- the shipped PREFIX entry points (general_cog.py command bodies;
    # goldens/general/sweep_fact..sweep_trivia pin the bytes). Each handler
    # draws EXACTLY ONE module-global random pick BEFORE opening the card —
    # the parity runner reseeds seed 42 per case, and the draw order
    # (choice, then the chat-award randint the message feed runs AFTER
    # dispatch) is what the goldens' content + XP bytes pin. --------------

    async def _open(req, panel_id: str, params: dict) -> None:
        import dataclasses

        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(
            PanelRef(panel_id),
            dataclasses.replace(req, args={**dict(req.args), **params}))

    @handler("general.fact_cmd")
    async def fact_cmd(req) -> None:
        """!fact — the shipped '💡 Random Fact' embed."""
        from sb.domain.general.content import FACTS, pick

        await _open(req, "general.card", {
            "card_title": "💡 Random Fact",
            "card_description": pick(FACTS, "facts")})

    @handler("general.joke_cmd")
    async def joke_cmd(req) -> None:
        """!joke — the shipped '😄 Random Joke' embed."""
        from sb.domain.general.content import JOKES, pick

        await _open(req, "general.card", {
            "card_title": "😄 Random Joke",
            "card_description": pick(JOKES, "jokes")})

    @handler("general.quote_cmd")
    async def quote_cmd(req) -> None:
        """!quote — the shipped '💬 Quote' embed."""
        from sb.domain.general.content import QUOTES, pick

        await _open(req, "general.card", {
            "card_title": "💬 Quote",
            "card_description": pick(QUOTES, "quotes")})

    @handler("general.motivate_cmd")
    async def motivate_cmd(req) -> None:
        """!motivate — the shipped '💪 Motivation' embed."""
        from sb.domain.general.content import MOTIVATIONS, pick

        await _open(req, "general.card", {
            "card_title": "💪 Motivation",
            "card_description": pick(MOTIVATIONS, "motivational messages")})

    @handler("general.greet_cmd")
    async def greet_cmd(req) -> None:
        """!greet — the shipped '👋 Greeting' embed: the drawn greeting +
        the invoker mention (``f"{random.choice(GREETINGS)}
        {ctx.author.mention}"``, general_cog.py verbatim)."""
        from sb.domain.general.content import GREETINGS, pick

        actor = int(getattr(req.actor, "user_id", 0) or 0)
        await _open(req, "general.card", {
            "card_title": "👋 Greeting",
            "card_description": f"{pick(GREETINGS, 'greetings')} <@{actor}>"})

    @handler("general.eightball_cmd")
    async def eightball_cmd(req) -> None | Reply:
        """!eightball <question> (alias !8ball) — the shipped '🎱 Magic
        8-Ball' embed: the non-inline Question/Answer field pair. The
        shipped signature required the question (``*, question: str`` —
        a bare ``!eightball`` died in bot1.py's MissingRequiredArgument
        envelope; no golden pins that path, so the guard is the repo's
        handler-owned usage line, trap-22 posture)."""
        from sb.domain.general.content import EIGHTBALL, pick

        question = str(req.args.get("text", "") or "").strip()
        if not question:
            return Reply(BLOCKED, "Usage: `!eightball <question>`")
        await _open(req, "general.card", {
            "card_title": "🎱 Magic 8-Ball",
            "card_fields": (("Question", question, False),
                            ("Answer", pick(EIGHTBALL, "8-ball answers"),
                             False))})
        return None

    @handler("general.trivia_cmd")
    async def trivia_cmd(req) -> None:
        """!trivia — the shipped question card + reveal button
        (general_cog.py: ``raw.split(" || ", 1)``; the answer rides the
        open args into the minted button binding, exactly the shipped
        ``_TriviaRevealView(ctx.author, answer)`` instance state)."""
        from sb.domain.general.content import TRIVIA, pick

        raw = pick(TRIVIA, "trivia questions")
        if " || " in raw:
            question, answer = raw.split(" || ", 1)
        else:
            question, answer = raw, None
        await _open(req, "general.trivia_card", {
            "trivia_question": question.strip(),
            "trivia_answer": answer})

    @handler("general.trivia_reveal")
    async def trivia_reveal(req) -> Reply:
        """The reveal click — general_cog.py ``reveal_btn`` verbatim:
        ``**Answer:** {text}`` ephemeral (the declared EPHEMERAL
        visibility on the action spec)."""
        answer = req.args.get("trivia_answer")
        text = str(answer).strip() if answer else "No answer recorded."
        return Reply(SUCCESS, f"**Answer:** {text}")


_register()


def ensure_handler_refs() -> None:
    _register()

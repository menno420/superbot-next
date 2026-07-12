"""Casino handlers (band 6 / parity flip) — the shipped cog + lobby-view
click semantics over the ported table registry (sb/domain/casino/table.py).

``!poker`` (cogs/casino_cog.py) and the hub's New Poker Table button
(views/casino/hub.py) share one launch path: refuse while a live table
holds the channel (each surface keeps its own shipped copy), else seat
the invoker as host and send the lobby panel
(``parity/goldens/casino/sweep_poker.json`` pins the open bytes).

The lobby clicks (Join/Leave/Start/Close) port the shipped
``PokerTable`` guard copies verbatim and edit the lobby message in
place through ``refresh_session_view`` (the rps/blackjack recipe; a
vanished session degrades to the text reply). The GAME layer past
``Start``'s lobby guards — dealing + per-player auto-updating EPHEMERAL
hand messages — is live-adapter work by construction (no headless
shape; D-0045 successor note): the pure deck (cards.py) + hand
evaluator (evaluate.py) are aboard, and ``Start`` past MIN_PLAYERS is
an honest blocked terminal until the live adapter arms. Play-chips
only — no economy leg anywhere (the goldens carry no economy rows)."""

from __future__ import annotations

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["Reply", "ensure_handler_refs"]

_POKER_PANEL = "casino.poker_table"


async def _display_name(req) -> str:
    """The shipped ``_display_name`` (display_name or name, 'Player'
    fallback) through the guild-directory read port — renderer paths
    carry no origin member object (the economy precedent); degrades to
    the shipped fallback, never invented data."""
    try:
        from sb.domain.utility.service import guild_directory

        member = await guild_directory().member_info(
            int(req.guild_id or 0), int(req.actor.user_id))
        return member.tag.rsplit("#", 1)[0] or "Player"
    except Exception:  # noqa: BLE001 — no directory ⇒ the shipped fallback
        return "Player"


async def _refresh_lobby(req, *, params: dict | None = None,
                         expire: bool = False) -> bool:
    """Edit the lobby message in place (the shipped auto-updating view;
    rps precedent) — False when no live session exists."""
    from sb.kernel.panels.engine import refresh_session_view

    message = getattr(req.origin, "message", None)
    message_key = str(getattr(message, "id", "") or "")
    if not message_key:
        return False
    return await refresh_session_view(
        req, message_key=message_key, params=dict(params or {}),
        expire=expire)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("casino.poker_open")):
        return

    @handler("casino.poker_open")
    async def poker_open(req):
        """!poker / !holdem + the hub's New Poker Table button — the
        shipped shared launch path (guard copy per surface)."""
        from sb.domain.casino.table import get_table, launch_table
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        channel_id = int(req.channel_id or 0)
        existing = get_table(channel_id)
        if existing is not None and not existing.ended:
            if req.args.get("session_action"):
                # the hub click's shipped ephemeral copy
                # (views/casino/hub.py).
                return Reply(BLOCKED,
                             "There's already an active poker table in "
                             "this channel — join that one (scroll up) "
                             "or wait for it to finish.")
            # the command's shipped channel copy (cogs/casino_cog.py).
            return Reply(BLOCKED,
                         "♠ There's already an active poker table in "
                         "this channel — join that one or wait for it "
                         "to finish.")
        launch_table(channel_id, int(req.actor.user_id),
                     await _display_name(req))
        await open_panel(PanelRef(_POKER_PANEL), req)
        return Reply(SUCCESS, None)

    @handler("casino.roulette_soon")
    async def roulette_soon(req) -> Reply:
        """The shipped Roulette callback (unreachable while the button
        ships disabled — views/casino/hub.py)."""
        return Reply(SUCCESS, "Roulette is coming soon!")

    @handler("casino.poker_join")
    async def poker_join(req):
        from sb.domain.casino.table import MAX_SEATS, get_table

        lobby = get_table(int(req.channel_id or 0))
        if lobby is None or lobby.ended:
            return Reply(BLOCKED, "This table has closed.")
        if lobby.started:
            return Reply(BLOCKED, "This game has already started.")
        uid = int(req.actor.user_id)
        if lobby.is_seated(uid):
            return Reply(BLOCKED, "You're already seated at this table.")
        if len(lobby.seats) >= MAX_SEATS:
            return Reply(BLOCKED, f"This table is full ({MAX_SEATS} seats).")
        lobby.seats.append((uid, await _display_name(req)))
        await _refresh_lobby(req)
        return Reply(SUCCESS, None)

    @handler("casino.poker_leave")
    async def poker_leave(req):
        from sb.domain.casino.table import close_table, get_table

        lobby = get_table(int(req.channel_id or 0))
        uid = int(req.actor.user_id)
        if lobby is None or lobby.ended or not lobby.is_seated(uid):
            return Reply(BLOCKED, "You're not seated at this table.")
        lobby.seats = [(u, n) for u, n in lobby.seats if u != uid]
        if not lobby.seats or uid == lobby.host_id:
            # host left / table emptied — the lobby folds (the shipped
            # teardown lane).
            close_table(lobby.channel_id)
            await _refresh_lobby(
                req, params={"stage": "closed",
                             "reason": "The host closed the table."},
                expire=True)
            return Reply(SUCCESS, None)
        await _refresh_lobby(req)
        return Reply(SUCCESS, None)

    @handler("casino.poker_start")
    async def poker_start(req):
        """Host presses ▶️ Start — DEAL the first hand through the ported
        betting engine and open the public spectator + action panel (the
        D-0045 successor: dealing is no longer a blocked terminal).  The
        per-player private hole cards render as a pure projection of the one
        engine snapshot (view.player_hand_view); their LIVE ephemeral
        delivery is the owner-armed live-adapter step, deferred."""
        from sb.domain.casino.game import start_game
        from sb.domain.casino.panels import POKER_GAME_PANEL_ID
        from sb.domain.casino.table import MIN_PLAYERS, get_table
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        lobby = get_table(int(req.channel_id or 0))
        if lobby is None or lobby.ended:
            return Reply(BLOCKED, "This table has closed.")
        if int(req.actor.user_id) != lobby.host_id:
            return Reply(BLOCKED, "Only the host can start the table.")
        if lobby.started:
            return Reply(BLOCKED, "This game has already started.")
        if len(lobby.seats) < MIN_PLAYERS:
            return Reply(BLOCKED,
                         f"Need at least {MIN_PLAYERS} players to start.")
        lobby.started = True
        start_game(int(req.channel_id or 0), list(lobby.seats))
        # the public spectator + action panel (CHANNEL_ANCHOR public send);
        # the lobby message stays put but its Join/Start clicks are inert
        # (guarded on ``lobby.started``).
        await open_panel(PanelRef(POKER_GAME_PANEL_ID), req)
        return Reply(SUCCESS, None)

    @handler("casino.poker_action")
    async def poker_action(req):
        """A play button on the public game panel (session-lifecycle binding
        → resolve() → here): run the mapped engine transition, then refresh
        the public spectator view IN PLACE (the blackjack solo-table recipe).
        Every click is gated to the seat whose turn it is — the host
        end-controls to the host (the shipped per-click authority)."""
        from sb.domain.casino.engine import Action, PokerError
        from sb.domain.casino.game import end_game, get_game
        from sb.domain.casino.table import close_table, get_table
        from sb.domain.casino.view import raise_targets
        from sb.kernel.panels.engine import refresh_session_view

        channel_id = int(req.channel_id or 0)
        game = get_game(channel_id)
        if game is None:
            return Reply(BLOCKED, "This hand has ended.")
        action = str(req.args.get("session_action") or "")
        uid = int(req.actor.user_id)
        lobby = get_table(channel_id)
        host_id = lobby.host_id if lobby is not None else 0
        message = getattr(req.origin, "message", None)
        message_key = str(getattr(message, "id", "") or "")

        # --- host end-of-hand controls ---------------------------------
        if action in ("poker_deal_next", "poker_end"):
            if uid != host_id:
                return Reply(BLOCKED, "Only the host can do that.")
            if not game.is_hand_over:
                return Reply(BLOCKED, "Finish this hand first.")
            if action == "poker_end":
                end_game(channel_id)
                if lobby is not None:
                    close_table(channel_id)
                await refresh_session_view(
                    req, message_key=message_key, params={}, expire=True)
                return Reply(SUCCESS, None)
            try:
                game.begin_hand()               # the shipped "Deal next hand"
            except PokerError:
                # fewer than two funded seats — the table folds (shipped).
                end_game(channel_id)
                if lobby is not None:
                    close_table(channel_id)
                await refresh_session_view(
                    req, message_key=message_key, params={}, expire=True)
                return Reply(SUCCESS,
                             "♠ Not enough funded players — the table closed.")
            await refresh_session_view(req, message_key=message_key, params={})
            return Reply(SUCCESS, None)

        # --- in-hand play actions (current seat only) ------------------
        current = game.current_player
        if current is None or int(current.user_id) != uid:
            return Reply(BLOCKED, "It's not your turn.")
        targets = raise_targets(game.snapshot())
        try:
            if action == "poker_fold":
                game.act(Action.FOLD)
            elif action == "poker_checkcall":
                game.act(Action.CHECK if game.to_call() == 0 else Action.CALL)
            elif action == "poker_raise_min":
                game.act(Action.RAISE, raise_to=targets["min"])
            elif action == "poker_raise_pot":
                game.act(Action.RAISE, raise_to=targets["pot"])
            elif action == "poker_allin":
                game.act(Action.RAISE, raise_to=targets["max"])
            else:
                return Reply(BLOCKED, "This session has expired — "
                                      "start a new one.")
        except PokerError as exc:
            return Reply(BLOCKED, f"♠ {exc}")
        refreshed = await refresh_session_view(
            req, message_key=message_key, params={})
        if not refreshed:
            return Reply(SUCCESS, "♠ Move recorded — "
                                  "waiting for the table view.")
        return Reply(SUCCESS, None)

    @handler("casino.poker_close")
    async def poker_close(req):
        from sb.domain.casino.table import close_table, get_table

        lobby = get_table(int(req.channel_id or 0))
        if lobby is None or lobby.ended:
            return Reply(BLOCKED, "This table has closed.")
        if int(req.actor.user_id) != lobby.host_id:
            return Reply(BLOCKED, "Only the host can close this table.")
        close_table(lobby.channel_id)
        await _refresh_lobby(
            req, params={"stage": "closed",
                         "reason": "The host closed the table."},
            expire=True)
        return Reply(SUCCESS, None)


_register()


def ensure_handler_refs() -> None:
    _register()

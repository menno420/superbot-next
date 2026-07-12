"""Poker PRESENTATION projections (band 6 play-layer port) — PURE readers
over one :meth:`sb.domain.casino.engine.PokerGame.snapshot` dict.

The shipped ``disbot/views/casino/poker_table.py`` rendered two live surfaces
per action — a PUBLIC spectator embed (``_refresh_public``) and a PRIVATE
per-seat hand embed edited into each player's auto-updating ephemeral message
(``_broadcast``).  The per-message ephemeral handles are the D-0045 "no
headless shape" wall.  This module keeps the SHAPE headless: every surface is
a deterministic function of the single engine snapshot, so the play layer
renders + tests without a live adapter, and the owner-armed live step only has
to DELIVER these projections to real ephemeral messages.

Copy carried verbatim from the shipped view (titles / field names / footers);
play-chips only — no coin/payout strings anywhere.
"""

from __future__ import annotations

__all__ = [
    "action_button_plan",
    "player_hand_view",
    "public_spectator_view",
    "raise_targets",
    "seat_lobby_view",
]

# GAME_COLOR purple (the golden pins 10181046 on every casino embed).
_STYLE_TOKEN = "purple"

# the shipped in-hand seat footer + the shipped end-of-hand host prompt.
_IN_HAND_FOOTER = "Blinds 5/10 · Texas Hold'em"
_END_FOOTER = 'Host: press "Deal next hand". Hands aren\'t restart-safe.'
_SEAT_FOOTER = "Texas Hold'em · play-chips"


def _cards(codes) -> str:
    return "  ".join(codes) if codes else "—"


def _player_by_id(snapshot: dict, user_id: int) -> dict | None:
    for p in snapshot.get("players", ()):
        if int(p["user_id"]) == int(user_id):
            return p
    return None


def _status_word(player: dict) -> str:
    if player.get("folded"):
        return "Folded"
    if player.get("all_in"):
        return "All-in"
    if player.get("sitting_out"):
        return "Sitting out"
    return "In hand"


def _result_lines(snapshot: dict) -> str:
    """The shipped 🏆 result copy — one line per winning seat."""
    lines = []
    by_id = {int(p["user_id"]): p["name"] for p in snapshot.get("players", ())}
    for res in snapshot.get("results", ()):
        name = by_id.get(int(res["user_id"]), "Player")
        if res.get("hand_label"):
            lines.append(f"{name} wins {res['amount']} with {res['hand_label']}.")
        else:
            lines.append(f"{name} wins {res['amount']} (everyone else folded).")
    return "\n".join(lines)


def seat_lobby_view() -> dict:
    """The shipped ``♠ You're seated!`` primer (pre-deal seat message) — a
    static projection carried for the owner-armed live seat send."""
    return {
        "title": "♠ You're seated!",
        "description": (
            "You've joined the poker table. When the host starts, your "
            "private hand will appear **right here** in this message and "
            "update live as everyone plays.\n\nEveryone starts with **1000** "
            "chips. Blinds are 5/10."),
        "footer": _SEAT_FOOTER,
        "style_token": _STYLE_TOKEN,
    }


def public_spectator_view(snapshot: dict) -> dict:
    """The PUBLIC spectator embed (``_refresh_public``): board / pot / hand
    number / seated players / result — NO hole cards (they stay private)."""
    complete = snapshot.get("stage") == "complete"
    players = snapshot.get("players", ())
    current_id = snapshot.get("current_user_id")
    seat_lines = []
    for p in players:
        marker = "▶ " if (not complete and int(p["user_id"]) == int(current_id or 0)) else ""
        tag = ""
        if p.get("folded"):
            tag = " · folded"
        elif p.get("all_in"):
            tag = " · all-in"
        seat_lines.append(f"{marker}{p['name']} — {p['stack']} chips{tag}")
    fields = [
        ("Board", _cards(snapshot.get("board", ()))),
        ("💰 Pot", str(snapshot.get("pot_total", 0))),
        ("Hand #", str(snapshot.get("hand_number", 0))),
        ("Players", "\n".join(seat_lines) or "—"),
    ]
    result = _result_lines(snapshot)
    if result:
        fields.append(("🏆 Result", result))
    if complete:
        description = result or "Hand complete."
        footer = _END_FOOTER
    else:
        cur = next((p["name"] for p in players
                    if int(p["user_id"]) == int(current_id or 0)), None)
        log = snapshot.get("log", ())
        recent = log[-1] if log else ""
        description = (f"**{cur}** to act." if cur else "Dealing…")
        if recent:
            description += f"\n_{recent}_"
        footer = _IN_HAND_FOOTER
    return {
        "title": "♠ Poker Table",
        "description": description,
        "fields": fields,
        "footer": footer,
        "style_token": _STYLE_TOKEN,
        "complete": complete,
    }


def player_hand_view(snapshot: dict, user_id: int) -> dict | None:
    """The PRIVATE per-seat hand embed (``_broadcast``): the seat's hole
    cards + the shared board/pot + their own turn state.  ``None`` when the
    user is not seated at this table (the shipped guard)."""
    player = _player_by_id(snapshot, user_id)
    if player is None:
        return None
    complete = snapshot.get("stage") == "complete"
    is_turn = (not complete
               and int(snapshot.get("current_user_id") or 0) == int(user_id))
    fields = [
        ("Your cards", _cards(player.get("hole", ()))),
        ("Board", _cards(snapshot.get("board", ()))),
        ("💰 Pot", str(snapshot.get("pot_total", 0))),
        ("🪙 Your stack", str(player.get("stack", 0))),
        ("Status", _status_word(player)),
    ]
    if is_turn:
        fields.append(("To call", str(snapshot.get("to_call", 0))))
    if complete:
        result = _result_lines(snapshot)
        if result:
            fields.append(("🏆 Result", result))
        footer = _END_FOOTER
    else:
        footer = _IN_HAND_FOOTER
    return {
        "title": "🟢 Your Hand — your turn!" if is_turn else "♠ Your Hand",
        "fields": fields,
        "footer": footer,
        "style_token": _STYLE_TOKEN,
    }


def raise_targets(snapshot: dict) -> dict:
    """The three shipped raise presets (⬆️ min · 🔥 pot · 💥 all-in) as
    absolute raise-TO totals, computed from the snapshot so the button label
    and the engine action agree (one formula, no drift).

    The ``pot`` preset is the oracle's own quick-bet value verbatim — a raise-TO
    of the whole ``pot_total`` (``menno420/superbot``
    ``disbot/views/casino/poker_table.py`` → ``pot_raise =
    min(max(lo, game.pot_total), hi)``), clamped into the legal
    ``[min_to, max_to]`` window.  It is deliberately NOT ``current_bet +
    pot_total`` (which would over-offer by ``current_bet`` whenever the player
    faces a bet), and NOT strict pot-limit (``pot_total + 2·call``)."""
    idx = snapshot.get("current")
    players = snapshot.get("players", ())
    if idx is None or idx < 0 or idx >= len(players):
        return {"min": 0, "pot": 0, "max": 0}
    p = players[idx]
    current_bet = int(snapshot.get("current_bet", 0))
    min_raise = int(snapshot.get("min_raise", 0))
    max_to = int(p["committed_round"]) + int(p["stack"])
    min_to = min(current_bet + min_raise, max_to)
    pot_to = min(max_to, int(snapshot.get("pot_total", 0)))
    return {"min": min_to, "pot": max(pot_to, min_to), "max": max_to}


def action_button_plan(snapshot: dict) -> dict:
    """Which action buttons the CURRENT player may press, with their live
    labels — the headless twin of the shipped dynamic ``SeatView``.  Keys are
    the panel action ids; values are ``{"enabled": bool, "label": str}`` so
    the renderer keeps a STABLE button layout (fold/check-or-call/raise
    presets in row 0, host end-controls in row 1) and only toggles state."""
    complete = snapshot.get("stage") == "complete"
    legal = dict(snapshot.get("legal_actions") or {})
    current_bet = int(snapshot.get("current_bet", 0))
    can_raise = "raise" in legal
    targets = raise_targets(snapshot) if can_raise else {"min": 0, "pot": 0, "max": 0}
    verb = "Bet" if current_bet == 0 else "Raise to"
    if "check" in legal:
        checkcall = {"enabled": True, "label": "Check"}
    elif "call" in legal:
        checkcall = {"enabled": True, "label": f"Call {legal['call']}"}
    else:
        checkcall = {"enabled": False, "label": "Check"}
    return {
        "poker_fold": {"enabled": (not complete) and bool(legal.get("fold")),
                       "label": "Fold"},
        "poker_checkcall": {**checkcall, "enabled": (not complete) and checkcall["enabled"]},
        "poker_raise_min": {"enabled": (not complete) and can_raise,
                            "label": f"{verb} {targets['min']}"},
        "poker_raise_pot": {"enabled": (not complete) and can_raise,
                            "label": f"{verb} {targets['pot']} (pot)"},
        "poker_allin": {"enabled": (not complete) and can_raise,
                        "label": f"All-in {targets['max']}"},
        "poker_deal_next": {"enabled": complete, "label": "Deal next hand"},
        "poker_end": {"enabled": complete, "label": "End table"},
    }

"""Characterization / posture-pin for the tournament open-flag guard.

The shared ``active_tournament`` open guard is a DELIBERATELY non-atomic
read-then-set: ``sb/domain/rps/handlers.py`` / ``blackjack/handlers.py``
read ``get_active`` and refuse a foreign game, then the open leg calls
``tournament_flag.set_active`` — a plain unconditional UPSERT. This mirrors
the superbot oracle verbatim; the narrow double-open window it leaves is
low-severity and boot-sweep-recovered.

``docs/ideas/tournament-open-flag-toctou-2026-07-12.md`` (``outcome:
accepted-posture``) ledgers this as INTENTIONAL: a strict atomic fence
(``ON CONFLICT ... WHERE`` compare-and-set + ``RETURNING``, or an advisory
lock) would diverge from the ported oracle and is an OWNER-DECISION, not an
autonomous fix. These tests pin the current behaviour so an accidental
"hardening" of ``set_active`` into a compare-and-set trips here and routes
the change back to that ledger instead of shipping a silent divergence.

NOTE (posture-pin, NOT a regression fix): this file changes NO production
behaviour. If a future owner-directed change intentionally makes the open
guard atomic, update this file together with the idea doc's decision.
"""

from __future__ import annotations

import asyncio

import pytest

run = asyncio.run

# parity/harness/world.py guild constant (matches the sibling band6 suites).
W_GUILD = 700_000_000_000_000_001


@pytest.fixture()
def captured_execute(monkeypatch):
    """Capture the SQL ``set_active`` issues without touching a DB — the
    real primitive runs, only its ``pool.execute`` sink is faked."""
    from sb.domain.games import tournament_flag as tf

    seen: dict[str, object] = {}

    async def fake_execute(query, params=None, *, conn=None):
        seen["query"] = query
        seen["params"] = params
        seen["conn"] = conn
        return "INSERT 0 1"

    # tournament_flag binds ``execute`` at import (``from ... import execute``),
    # so patch the name in its namespace, not the pool module.
    monkeypatch.setattr(tf, "execute", fake_execute)
    return seen


def test_set_active_is_unconditional_upsert_accepted_nonatomic_posture(
        captured_execute):
    """PIN: ``set_active`` is a plain unconditional UPSERT — NOT a
    compare-and-set. No ``WHERE`` guard on the ``ON CONFLICT`` arm and no
    ``RETURNING`` read-back means two racing DIFFERENT-game opens both
    write (the accepted, oracle-faithful non-atomic window). If someone
    "fixes" this into an atomic CAS the SQL grows a ``WHERE`` / ``RETURNING``
    and this assertion fails — by design; see
    docs/ideas/tournament-open-flag-toctou-2026-07-12.md (accepted-posture)."""
    from sb.domain.games import tournament_flag as tf

    result = run(tf.set_active(object(), guild_id=W_GUILD, game="rps"))

    q = " ".join(str(captured_execute["query"]).upper().split())
    assert "INSERT INTO GUILD_SETTINGS" in q
    assert "ON CONFLICT (GUILD_ID, KEY) DO UPDATE SET VALUE = EXCLUDED.VALUE" in q
    # the pinned non-atomic posture: no compare-and-set guard, no read-back.
    assert "WHERE" not in q, (
        "open guard must stay an unconditional UPSERT (accepted-posture); a "
        "compare-and-set fence is an owner-decision — see "
        "docs/ideas/tournament-open-flag-toctou-2026-07-12.md")
    assert "RETURNING" not in q, (
        "open guard must not read back a win/lose signal (accepted-posture); "
        "see docs/ideas/tournament-open-flag-toctou-2026-07-12.md")
    # an unconditional upsert reports nothing — not a bool CAS win/lose token.
    assert result is None
    # the row bytes the rpsregister golden pins.
    assert captured_execute["params"] == (int(W_GUILD), "active_tournament", "rps")


def test_set_active_write_bytes_are_stable_own_and_foreign_game():
    """Companion pin: the guard writes ``value=<game>`` for whatever game
    opens — it does not consult or compare the existing row (the non-atomic
    posture again). Both an own-game re-arm and a foreign clobber issue the
    SAME unconditional upsert shape."""
    from sb.domain.games import tournament_flag as tf

    seen: list[tuple] = []

    async def fake_execute(query, params=None, *, conn=None):
        seen.append(params)
        return "INSERT 0 1"

    tf_execute = tf.execute
    try:
        tf.execute = fake_execute  # type: ignore[assignment]
        run(tf.set_active(object(), guild_id=W_GUILD, game="rps"))
        run(tf.set_active(object(), guild_id=W_GUILD, game="blackjack"))
    finally:
        tf.execute = tf_execute  # type: ignore[assignment]

    assert seen == [
        (int(W_GUILD), "active_tournament", "rps"),
        (int(W_GUILD), "active_tournament", "blackjack"),
    ]

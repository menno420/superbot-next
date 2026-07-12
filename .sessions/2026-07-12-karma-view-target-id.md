# 2026-07-12 — karma view lane resolves target from argv[0] only (the treasury-karma card's ledgered sibling)

> **Status:** `complete`

- **📊 Model:** Claude (Fable family) · scan-class parse fix, view lane

## Scope

The follow-up the `2026-07-12-treasury-karma-argv-fix.md` card ledgered
in its sibling scan (lines 90-94): `sb/domain/karma/handlers.py`
`_target_id` (:29-34) kept the first-digit-token whole-argv scan shape
that #275/#290 removed from the mutation lanes. It serves ONLY
`karma.card_view` (`!karma [@user]`, optional-member pure READ), so a
digit token deep in argv bound as the card TARGET —
`!karma some text 123456789012345678` showed the wrong user's card.

Fix: rebind `_target_id` to argv[0] ONLY (mention `<@id>`/`<@!id>` or
bare ID), mirroring `ops.py::_target_from`'s positional shape (#290) —
but KEEP the `return None`/actor-fallback tail: the shipped command was
`karma(ctx, member: discord.Member | None = None)` (an Optional
converter — discord.py backtracks to the default on a failed
conversion), so a non-convertible or absent argv[0] falls back to the
actor's own card, byte-identical to today. No BadArgument raise in this
lane.

## Oracle semantics (verified this session)

`/workspace/superbot/disbot/cogs/karma_cog.py:222-233` (shallow clone,
HEAD `97d281e`): `@commands.group(name="karma",
invoke_without_command=True)` → `async def karma(self, ctx, member:
discord.Member | None = None)` → `target = member or ctx.author`.
Optional converter semantics: failed conversion of argv[0] backtracks
to `None` → actor's card. Actor fallback confirmed; the raise belongs
only to the mutation lane (required `member:` slot).

## Delivered

- `sb/domain/karma/handlers.py` — `_target_id` parses argv[0] only;
  None tail kept.
- `tests/unit/band4/test_band4_karma.py` — 3 card-view target tests:
  deep digit token no longer selected (REGRESSION — verified red on the
  old body: `assert 123456789012345678 is None` failed before the fix),
  argv[0] mention/bare-ID still selected, non-convertible argv[0] and
  empty argv return None (actor fallback).

## Evidence

- units: `python3 -m pytest tests/ -q` → 2039 passed, 13 skipped.
- red→green: regression test FAILED against the pre-fix `_target_id`
  (whole-argv scan returned 123456789012345678), passes after the
  argv[0]-only rebind; band4 karma suite 14/14.
- kit gate: `python3 bootstrap.py check --strict` → only the designed
  born-red hold on this card's in-progress badge (flipped in the
  landing commit) + two pre-existing rps-claims advisory warnings, not
  this lane.

## 💡 Session idea

`_target_id` (handlers) and `_target_from` (ops) now encode the same
argv[0] mention/bare-ID parse in two shapes — a tiny shared
`parse_member_token(token) -> int | None` in the karma domain (or the
handler kit, if a third caller appears) would make the next scan-class
regression impossible to reintroduce in one lane only.

## ⟲ Previous-session review

The `2026-07-12-treasury-karma-argv-fix.md` card's sibling scan (lines
90-94) made this slice nearly free: exact symbol, exact lines, exact
"view lane, actor fallback, not this slice's shape" boundary. What it
could have done better: it left the oracle nuance for the OPTIONAL
member slot unverified (raise vs backtrack) — this session had to pull
the shipped cog to confirm discord.py's Optional-converter backtrack
before knowing the None tail was the right keep.

# 2026-07-12 — karma view lane resolves target from argv[0] only (the treasury-karma card's ledgered sibling)

> **Status:** in-progress

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
- `tests/unit/band4/test_band4_karma.py` — card-view target resolution
  tests: deep digit token no longer selected (regression, verified red
  on the old body), argv[0] mention/bare-ID still selected,
  non-convertible argv[0] and empty argv return None (actor fallback).

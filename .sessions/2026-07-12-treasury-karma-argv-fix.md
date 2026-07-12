# 2026-07-12 — treasury grant + karma thanks argv parse fix (owner directive slice 5, the two sibling scan-class defects #275 noted)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · scan-class parse fixes, oracle-pinned positional binding (Q-0194)

## Scope

One bounded slice: the two remaining first-digit-token argv parse
defects — the same class as the just-merged givexp fix (#275, merge
`7af1605`), both explicitly NOTED-not-fixed in that PR's sibling scan:

1. `sb/domain/treasury/ops.py` `_amount_from` (was :49-71) scanned argv
   for the FIRST digit token, so on `!treasury grant <bare_id> <amt>`
   the bare snowflake target double-read as the AMOUNT — the pool-balance
   check refused ~9e17 coins (loud, but the wrong parse).
2. `sb/domain/karma/ops.py` `_target_from` (was :89-100) scanned all of
   argv for the first digit token instead of binding argv[0], so a digit
   in the reason tail could bind as the TARGET (`!thanks bob 5` thanked
   user id 5); amount there is param-only (default 1), no amount half.

Both defects VERIFIED against source at origin/main HEAD (`7af1605`)
before fixing — present exactly as described.

## Oracle semantics (verified, not assumed)

Reconstructed via `mcp__github__search_code` over `menno420/superbot`
(fragments at indexed ref `f5071fb3d4aa…`): both shipped commands were
strictly POSITIONAL —

- `disbot/cogs/treasury_cog.py`: `async def grant(self, ctx, member:
  discord.Member, amount: int)` (aliases disburse/payout) and
  `async def contribute(self, ctx, amount: int)` — grant's amount is
  slot 1, contribute's is slot 0.
- `disbot/cogs/karma_cog.py`: `async def thanks(self, ctx, member:
  discord.Member, *, reason: str | None = None)` (aliases rep/thank;
  `!karma add` rides the same shape) — member is argv[0] ONLY, the
  keyword-only `reason` consumed EVERYTHING after it.
- Error arm VERIFIED for both lanes: neither karma_cog nor treasury_cog
  defines a local error handler (grep over each file: zero `error`
  handler hits beyond user copy), so `disbot/bot1.py`'s global
  `on_command_error` BadArgument arm rendered MemberNotFound as
  `⚠️ Bad argument: {error}` — the SAME arm #275 pinned; copy reused
  byte-for-byte: `⚠️ Bad argument: Member "X" not found.`

## Golden check (VERIFIED, not assumed)

- treasury grant is sweep-EXCLUDED entirely (`parity/cases/sweep.py`
  EXCLUDED_COMMANDS: "treasury first-touch init rides a real-TTL
  in-memory cache") — NO golden pins the grant lane at all; nothing to
  re-cut. `sweep_treasury_contribute` drives `!treasury contribute 3`
  (amount at slot 0 — unchanged binding) and replays byte-identical.
- karma goldens drive the mention form only (curated
  `!thanks <@900000000000000103> for the parity help` /
  `!thanks <@…>`; sweep synthesizes `<@900000000000000103>` for every
  Member param) with digit-free reasons — the bare-ID and digit-in-tail
  lanes are golden-UNPINNED; no golden pins the buggy behavior, no
  re-cut needed. Gate GREEN locally with both fixes (see Evidence).

## Delivered

- `sb/domain/treasury/ops.py` — `_amount_from` takes a positional
  `slot` (contribute slot 0, grant slot 1; `amount` param still wins;
  modal non-numeric rejection copy kept verbatim); `_record_disburse`
  binds the target from argv[0] ONLY (mention `<@id>`/`<@!id>` or bare
  ID; the old ≥15-digit whole-argv scan removed) — a non-digit argv[0]
  raises the pinned bot1.py BadArgument copy; param paths
  (`target_id`/`member`, panel lanes) untouched. NO FOR UPDATE /
  advisory-lock code touched — arg parsing only; check_money_race green.
- `sb/domain/karma/ops.py` — `_target_from` binds argv[0] ONLY (mention
  or bare ID; params `target_id`/`member` still win; the reaction lane
  is param-only and unaffected); a non-digit argv[0] raises the pinned
  BadArgument copy instead of scanning deeper. `_reason_from` joins
  argv[1:] verbatim (the shipped keyword-only rest) — the old
  digit-filter was the scan's other half and silently ate digit tokens
  inside the reason (`!thanks @bob 5 stars` recorded "stars"); flagged
  inline per PL-001, same positional semantics, same diff.
- `tests/unit/band3/test_band3_treasury_inventory.py` — 3 new tests:
  positional parse (bare-ID+amount, `<@!id>`+amount), the REGRESSION
  pin (bare ID must never become the amount — 5, not 9e17; pool debited
  5), failure copy (unknown-member byte-form; member-only must NOT
  double-read the snowflake as the amount).
- `tests/unit/band4/test_band4_karma.py` — 2 new tests: positional
  parse (bare-ID target + reason; mention + digit-in-reason keeps "5
  stars" and targets 7 not 5), the REGRESSION pin (`!thanks bob 5` must
  never thank user id 5 — BadArgument copy byte-form, nothing written).

## Sibling scan (same defect class, this slice's boundary)

- `sb/domain/karma/handlers.py` `_target_id` (:29-34) — the SAME
  first-digit scan shape, but it serves ONLY `karma.card_view`
  (`!karma [@user]`, optional-member pure READ with actor fallback);
  the mutation lane goes through ops. Left alone — follow-up note, not
  this slice's shape.
- deathmatch `_target_from_args` — already cleared in #275's scan.

## Evidence

- units: `python3 -m pytest tests/ -q` → 1745 passed, 2 skipped, 11
  failed — ALL 11 failures reproduced at CLEAN origin/main (`7af1605`)
  in a separate pristine worktree (integration race tests +
  btd6_seed_data; local-Postgres environment state, pre-existing, not
  this diff). Targeted suites: band3 treasury + band4 karma 27/27.
- money guard: `python3 tools/check_money_race.py` → OK, 0 violations
  (2 allowlisted, 0 ledgered known-risk).
- golden gate local: `python3 tools/run_golden_parity.py --gate` →
  GREEN — 427/427 goldens across 51 ported subsystems, with the fix.
- depth: `check_parity_depth` OK (51 subsystems, kernel ported, 468
  goldens).

## Codex

Question posted on the PR head per the directive; codex is currently
usage-capped — outcome recorded in the PR thread (non-review noted here
if it replies with a limits message).

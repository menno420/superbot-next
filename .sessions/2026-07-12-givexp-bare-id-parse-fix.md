# 2026-07-12 — `!givexp <bare_id> <amount>` parse fix (owner directive slice 3, the audit's one golden-unpinned admin defect)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · admin-defect fix, oracle-pinned positional parse (Q-0194)

## Scope

One bounded slice: fix the admin-surface audit's single FIX-list code
defect — `!givexp <bare_user_id> <amount>` misparsed because BOTH argv
helpers in `sb/domain/xp/ops.py` grabbed the FIRST digit token of argv:
`_target_from` (was :58-70) resolved the bare snowflake as the target
(correct) and `_amount_from` (was :73-88) then took the SAME snowflake
as the amount — awarding ~9.0e17 XP (a 9.0e17 snowflake ID becomes the
delta). Mention form was safe only because `<@id>` fails the amount
loop's `isdigit` test.

## Oracle semantics (Step 1)

Reconstructed via `mcp__github__search_code` over `menno420/superbot`
(direct file reads DENIED for this seat; fragments at indexed ref
`b7d017d9eece…`): the shipped command was strictly POSITIONAL —
`disbot/cogs/xp_cog.py`: `async def givexp(self, ctx, member:
discord.Member, amount: int)` (and `resetxp(self, ctx, member:
discord.Member)`), so discord.py bound argv[0] to MemberConverter
(ID → mention → name) and argv[1] to int; a later digit token was NEVER
the target and the first was NEVER the amount. On an unresolvable
member, MemberConverter raised `MemberNotFound('Member "X" not
found.')` and `disbot/bot1.py`'s global handler sent
`⚠️ Bad argument: {error}` (delete_after=10) — copy pinned verbatim.

## Golden check (VERIFIED, not assumed)

`parity/goldens/xp/sweep_givexp.json` drives ONLY the mention form
(`!givexp <@900000000000000103> 3`) — the bare-ID lane is
golden-UNPINNED, confirmed; no golden pins the buggy behavior, so no
re-cut was needed. The mention lane replays byte-identical after the
fix (gate GREEN locally, see Evidence).

## Delivered

- `sb/domain/xp/ops.py` — `_target_from` resolves argv[0] ONLY
  (mention `<@id>`/`<@!id>` or bare ID; param paths `target_id`/`user`
  unchanged, actor fallback only when argv is empty); a non-digit
  argv[0] raises the pinned bot1.py BadArgument copy instead of
  silently falling back to the actor (the resetxp-on-a-name
  wrong-target twin, same defect class, fixed by the same helper).
  `_amount_from` reads argv[1] ONLY — never a scan — with the existing
  "❌ Amount must be a whole number of XP." copy kept.
- `tests/unit/band4/test_band4_xp.py` — 4 new tests: positional parse
  (mention+amount, bare-ID+amount, `<@!id>` form), the REGRESSION pin
  (bare ID must never become the amount — delta 5, not 9e17), failure
  copy (unknown-member byte-form, garbage amount, amount-only), and
  the resetxp positional/no-actor-fallback twin.

## Sibling commands checked (same defect class)

- `sb/domain/xp` — resetxp: same helper, fixed here (target-only
  command, so its bare-ID lane already worked; the name→actor silent
  fallback was its real twin). xp has no takexp/setxp (oracle had
  none either — givexp/resetxp only).
- `sb/domain/treasury/ops.py` `_record_disburse`/`_amount_from`
  (:49-71, :121-132) — SAME first-digit-token amount scan: `!treasury
  grant <bare_id> <amount>` reads the snowflake as the amount (fails
  loudly on the treasury balance check rather than paying out, so
  lower severity). NOT fixed here — different lane copy + its own
  oracle semantics to pin; noted as a follow-up.
- `sb/domain/karma/ops.py` `_target_from` (:89-100) — scans all argv
  for the first digit token but amount is param-only (default 1), so
  no amount misparse; a digit-bearing reason token could mis-target.
  Follow-up note, not this slice's shape.
- `sb/domain/deathmatch/service.py` `_target_from_args` (:93-104) —
  target-only, 15-21-digit anchored regex; not affected.

## Evidence

- units: `python3 -m pytest tests/ -q` → 1744 passed, 2 skipped
  (canonical order, real Postgres; run at the pre-#265 base — re-run
  green in this worktree at `6e8c666`, see PR).
- golden gate local: GREEN (412/412 across 51 at base `dd76427`, and
  re-run GREEN at `6e8c666` post-forward-base 425/425) — zero golden
  movement from this fix.
- `check_money_race: OK — 0 violations under sb/domain (2 allowlisted
  site(s), 0 ledgered known-risk site(s))` — FOR UPDATE/advisory-lock
  paths untouched.
- One measurement artifact worth recording: a full-suite pytest run
  against the shared local Postgres immediately before a gate run left
  state that produced a spurious gate RED (177 diffs, all
  `$.db_delta.xp: missing`); the paired clean re-runs (gate GREEN at
  clean HEAD AND gate GREEN with this fix applied) isolated it as
  environmental, not a regression.

## 💡 Session idea

The first-digit-token argv scan is a repo-wide anti-pattern seeded by
copy-paste between domain `ops.py` files (xp fixed here; treasury has
the live amount-scan twin; karma the target-scan half). A cheap
checker in the fleet — flag any `for token in argv` loop that feeds an
`amount`/`target` binding — would kill the class the way
check_money_race killed F-001/F-002.

## ⟲ Previous-session review

The admin-surface audit's FIX row was a precise work order
(file:line, both offending helpers, the ~1.2e17 consequence, the
oracle pointer) and its "golden-unpinned" claim VERIFIED true. What it
under-specified: the silent actor-fallback twin (`!resetxp <name>`
resetting the CALLER's XP) that lives in the same helper — found only
by re-deriving the oracle's converter semantics rather than patching
the amount loop alone.

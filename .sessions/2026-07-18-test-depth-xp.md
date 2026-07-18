# 2026-07-18 — xp test-depth: permission gates + rank_view refusals + level-curve boundaries + migrate formats + seams

> **Status:** `in-progress`

- **📊 Model:** [[fill: model · effort · slice]]

## Scope

Test-depth coverage for `sb/domain/xp`: the hub/config permission-gate +
confirm fence, the `rank_view` refusal + arg-walk surface, the
givexp/resetxp handler copy, the level-curve boundary sweep, the remaining
migrate formats, the `resolve_text_channel`/`fetch_avatar_png` seams, the
level-up fan-out, and INV-G's check/repair legs.

Additive tests ONLY — no product code changes, no golden, DB-free
(`FakeXpStore` + monkeypatch, and `sb.kernel.db.pool` monkeypatched for the
two INV-G legs). New file `tests/unit/band4/test_band4_xp_depth.py`
(18 focused cases). Born-red card, tests second, flip-last; server-side
lander on green.

## Deliver — 18 DB-free cases

**P1 permission gates (pure spec reads):** hub tier gates (`rank`=user,
config/givexp/resetxp=admin floor); the `resetxp` irreversible typed-phrase
confirm fence + `destructive`; all four config actions admin-floor; the
`hub_overview` access-projection (Your rank/Messages only for a real actor).

**P1 rank_view (zero prior tests):** the name-token BLOCKED fallback; the
stat (xp/coins/both) + `<@id>` member arg-walk (open_panel patched); a
category token routing to `member_rank` (empty-hint vs `Rank #N`); the
givexp/resetxp handler copy (usage BLOCKED / non-SUCCESS passthrough /
SUCCESS ack).

**P2 math + migrate:** the level-curve boundary sweep L=0..20 (+ one-below);
`level_progress(0)`/`level_progress(-5)` contract (no infinite loop); the
mee6/superbot/generic formats + bold tolerance + first-mention-wins.

**P2/P3 seams:** `resolve_text_channel` (mention/snowflake/short/raise);
`fetch_avatar_png` (no fetcher/raise/bytes); the fan-out unbound + granter
swallow; INV-G `check_level_consistency` (flag vs clean) and the repair leg
(re-derive vs row-gone).

## Verification

- `python3 -m pytest tests/unit -q` → [[fill: verbatim tail]]
- `python3 tools/check_namespace.py` → clean
- `python3 tools/check_no_skip.py` → clean

## Deviation ledger

[[fill: store-SQL DB-backed follow-up + the Q-0120 dead-guard finding + any skipped gaps]]

## 💡 Session idea

[[fill: one idea]]

## ⟲ Previous-session review

[[fill: review of the most recent OTHER .sessions card]]

## Close-out

[[fill: PR # + test count]]

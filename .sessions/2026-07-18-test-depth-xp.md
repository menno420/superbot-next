# 2026-07-18 — xp test-depth: permission gates + rank_view refusals + level-curve boundaries + migrate formats + seams

> **Status:** `complete`

- **📊 Model:** opus-4.8 · high · test-depth (born-red, additive, DB-free)

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

- `python3 -m pytest tests/unit -q` → `3358 passed, 2 skipped, 1 warning in 69.97s` (full unit suite, per the ref-table lesson)
- `python3 tools/check_namespace.py` → `check_namespace: clean`
- `python3 tools/check_no_skip.py` → `check_no_skip: clean (every surface funnels through resolve())`

## Deviation ledger

- **store.py SQL is DB-backed → follow-up.** `add_xp` / `set_imported_xp` /
  `top_xp` + `all_xp_ordered` ordering / `erase_subject_xp` are real
  Postgres statements; they cannot be exercised DB-free and the `FakeXpStore`
  seam only stands in for their *callers*. Left for a DB-harnessed slice —
  not attempted here (per task guidance).
- **Q-0120 finding — the ops.py negative-level guard is DEAD via the records
  path.** `_record_import` runs `reduce_max_levels` first, whose `-1`
  sentinel (`level > best.get(user_id, -1)`) drops any level < 0 before the
  `if level < 0: raise` guard ever sees it (a lone `(7, -1)` reduces to `{}`
  ⇒ no write, no raise). Gap-10's "records `(user, -1)` → ValidatorError" is
  therefore unreachable as literally written. `test_import_negative_level_guard`
  pins BOTH truths: the natural path imports nothing, and forcing a negative
  past the reducer (monkeypatched) still fires the guard verbatim.
  **Guard recipe** for a later cleanup: either drop the dead `level < 0` arm
  in `sb/domain/xp/ops.py:_record_import` (~L182-185), or move the check
  ahead of `reduce_max_levels` so raw records are validated — test target
  `tests/unit/band4/test_band4_xp_depth.py::test_import_negative_level_guard`.
- **No gaps padded.** All 16 listed gaps are covered (gaps 1-16); gap 10 was
  reframed as above rather than dropped. INV-G shape (gap-adjacent) already
  had `test_inv_g_spec_shape` in the base file — the new tests add the
  check-provider + repair-leg *behavior* it did not cover.

## 💡 Session idea

The `hub_overview` / `config_overview` providers and `_render_config` each
independently re-read `service.xp_config` + `service.bound_announce_channel`
and re-format the same `<#id>` / "Same channel as message" string — three
copies of one projection. A single `xp_settings_view(guild_id)` read model
returning the formatted fields would collapse the drift surface and give the
renderers one seam to stub. Low-cost, and it would let the config-panel embed
bytes be pinned without a golden.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-setup-except-boundary-tests.md` (C1
except-density audit, #538 class) — the closest sibling: an additive,
born-red, DB-free characterization slice that pins `setup/moderation.py`'s
four `except` swallows (2 fail-CLOSED refusals, 2 informational fail-soft
degrades) without touching product behavior. Its posture is sound and its
"survey-then-pin-the-densest-cluster" method is exactly the discipline this
xp slice mirrors one band over. One caution its own 💡 already flags: its
whole-suite run was skipped locally (a `yaml`-gap + pytest-randomly
pollution) and leaned on CI for the sweep — this xp session did run the FULL
`tests/unit` locally (green, 3358) per the ref-table lesson, so the two cards
together show both the constrained and the full-local verification postures
side by side. Confirms the setup/role and now band-4 xp seams are the current
test-depth frontier.

## Close-out

PR **#542** (menno420/superbot-next) — `tests/unit/band4/test_band4_xp_depth.py`,
**18 DB-free cases**, additive only. Full unit suite + both guards green;
server-side lander on green. Branch `claude/test-depth-xp`.

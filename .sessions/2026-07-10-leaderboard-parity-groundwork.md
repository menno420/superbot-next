# 2026-07-10 — leaderboard parity groundwork (board panel to the shipped shape; flip withheld)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Drive `!leaderboard` (no category) to the shipped overview-panel shape
against `parity/goldens/leaderboard/sweep_leaderboard.json` — groundwork
only: the `parity.yml` pending→ported flip is deliberately NOT in this
slice. Oracle: menno420/superbot `disbot/cogs/leaderboard_cog.py`
(LeaderboardView).

## What shipped

1. **`!leaderboard` opens the board panel** — `leaderboard.board_view`
   with no category now returns `PanelRef("leaderboard.board")` instead of
   replying with a plain content string (`sb/domain/community/handlers.py`).
2. **Board spec pinned to shipped bytes** (`sb/domain/community/panels.py`)
   — `style_token "blue"` (3447003), `FooterMode.NONE`, selector-only row,
   `session_lifecycle=True`, rich select options (label/emoji/value fed
   from provider `select_label`/`select_emoji`).
3. **Shipped canonical provider order** —
   `rank_providers.provider_names()` returns xp, coins, mining, creatures,
   fishing, farm, gamexp, crafting, deathmatch, rps, counting, karma.
4. **Anchor-registry fidelity** — `_record_anchor` skips
   `session_lifecycle` panels (the shipped `panel_anchors` registry held
   panel-manager panels only; timeout-bound session views were never
   anchored; `help.home` still anchors).
5. **Cross-lane 3-string grant applied** — the band-6 games session
   granted option (c): `sb/domain/games/providers.py` gamexp
   `select_label` "World Level"→"Game Level", gamexp `select_emoji`
   🌍→🎮, crafting `select_emoji` →🔧 (the oracle wrench), strings only.
   No decision record exists for the "World Level" rename (checked inbox
   ORDERs, control/status.md, ideas ledgers at ec2bcf2) — a fidelity bug
   per parity doctrine.

## Why the flip is not here

The slice started with 4 residual byte-diffs, all outside this lane:
3 presentation strings owned by the games lane (cleared mid-slice by the
grant above) and the run-minted-custom_id class — goldens pin `<cid:1>`
where discord.py auto-minted 32-hex view ids. That last class was cleared
on main by #117 (`_mint_ephemeral`: session-lifecycle panels get
run-minted 32-hex ids, which the Normalizer symbolizes as `<cid:N>`).
After rebasing onto #117 + the string grant, the leaderboard golden
replays CLEAN (report leg: `leaderboard 1/1 green [pending]`) — the flip
is unblocked and belongs to a follow-up slice as its own deliberate
last-commit change.

Gate leg GREEN (4/4 goldens, 2 ported subsystems, real Postgres); pytest
1169 passed / 2 skipped; manifest_compile, check_compat_frozen,
check_parity_depth all green.

## 💡 Session idea

Both of this slice's blockers dissolved without any leaderboard-lane work
(one cross-lane grant, one kernel change riding in on rebase). A cheap
pre-PR ritual for every parity slice: rebase onto main and re-run the
report leg BEFORE writing the "blocked on" list — blocker inventories go
stale within hours when multiple lanes are landing fidelity fixes into
one shared kernel.

## ⟲ Previous-session review

The prior worker's residual-diff inventory (4 diffs, all cross-lane) was
exactly right at its HEAD and made this slice mechanical: the grant
request could name the 3 strings precisely, and the `<cid:N>` class was
already articulated well enough for D-0061/#117 to resolve it in another
lane. What it under-delivered: the branch's `_record_anchor`
session-lifecycle skip duplicated a guard #117 was landing at the call
site — harmless (defense in depth at the recorder), but two lanes
independently authored the same fidelity rule because the shipped
"panel_anchors held manager panels only" fact lived in neither a decision
record nor a kernel comment until both wrote it.

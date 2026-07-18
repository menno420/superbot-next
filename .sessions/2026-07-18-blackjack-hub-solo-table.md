# 2026-07-18 — blackjack hub-button solo flow: route the interactive table view

> **Status:** `in-progress`
>
> Born-red FIRST commit (this card + the claim) — holds the HOLD gate red so
> parallel sessions see the in-flight work and the lander waits. The
> implementation + tests land in the second commit; the deliberate LAST commit
> flips this badge to `complete`.

- **📊 Model:** [[fill:model-family · effort · task-class]]

## Scope

Item 5 of `docs/ideas/blackjack-remaining-surface-2026-07-10.md` — the
**hub-button solo flow**. The `blackjack.hub` panel's **Solo Free Play**
(`bj_solo_free`) and **Solo Bet** (`bj_solo_bet`, the G-10 bet modal) actions
route the bare `blackjack.solo_start` op with a `RESULT_CARD` — a static deal
with NO Hit/Stand/Double — while the shipped `!blackjack` command path
(`blackjack.play`) deals through `solo_start` and OPENS the interactive
`blackjack.table` session-lifecycle view. Unify both hub buttons onto ONE new
`blackjack.hub_solo` handler that mirrors the command path (deal → open the
table), the `casino.poker_open` command+button precedent.

Contained routing-correctness fix, no golden touched (the table wire shape is
already golden-pinned by `parity/goldens/blackjack/`; this only changes which
surface the hub buttons land on). DB-free additive tests.

## Deliver

- [[fill:handler + panel wiring delivered]]
- [[fill:tests added]]

## Verification

- [[fill:pytest result tail]]

## Deviation ledger

- [[fill:brief-vs-tree deviations]]

## Close-out

- [[fill:PR # + URL, branch, CI]]

## 💡 Idea

[[fill:one genuine idea]]

## ⟲ Previous-session review

[[fill:one-line previous-session review remark]]

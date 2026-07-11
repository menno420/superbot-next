# 2026-07-11 — band-7 continuation session (Knowledge + AI, continuous mode Q-0265)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194 / ORDER 012)

## Scope

The band-7 builder lane REOPENED post-wrap (the #181 wrap-up card is the
predecessor) and ran continuously per Q-0265 — slice after slice, each its
own squash-merged-on-green PR on the 6-check ruleset. Eight PRs merged
this continuation; every sha below verified against origin/main at
`0e7cacd0` (main HEAD, #208's merge). The session ended on the OWNER
WRAP-UP DIRECTIVE (archive-prep): enders only, no new slices — this card,
its telemetry row, the retro lessons doc, the CAPABILITIES.md wall record
and the final status fold ride the wrap-up PR.

## The eight PRs (one line each)

1. **#185** `168ef808` — behavior-preset slice (D-0071): migration 0030
   (`ai_instruction_profile` + the 7 seeded system presets), the
   behavior Channel/Category/Preview/Preset pickers live, `apply_preset`
   over the existing audited policy ops; NEW `seeded-catalog` depth
   reason class.
2. **#187** `d9c6b35a` — orchestration-mutation slice (D-0072):
   migration 0031, the tools Guild/Channel/Category/Preview profile
   pickers live, 3 audited `ai.set_*_orchestration` ops, K10 resolver
   consumption; codex 3 line findings fixed in-PR, 1 declined with
   oracle citation.
3. **#192** `14e5037` — lane heartbeat (the #185/#187 fold, post-#187
   counts).
4. **#194** `4024624d` — replay MODAL vocabulary + btd6 strategy-form
   goldens (D-0073, the D-0066 successor): the `modal` step kind, the
   first 2 MINTED goldens (corpus 465→467), the btd6.strategy_form
   modal on the audited `btd6.submit_strategy` op, the D-0063 deletion
   clause executed (btd6 ratchet tables 3→4); codex P2 verified real
   but declined with doctrine citation (A-16-clause-3).
5. **#199** `029b4001` — hygiene: `--write-ratchet` becomes a
   byte-preserving TEXT SPLICE of only the depth.ratchet block (the
   #144-ledgered comment-destruction fix, 9 pins) + the tests/unit/ai
   dir-wide after-only conftest reset (orchestration keeps a slim
   documented pre-leg — pure after-only empirically regresses #156);
   3 codex P2s all verified real and fixed in-PR.
6. **#204** `f82ac804` — routing-matrix picker (D-0074, the D-0071
   re-scope follow-up): oracle views/ai/routing/matrix.py ported whole
   over the verbatim resolve_policy dry-run; the LAST chooser pending
   terminal retired — every views/ai/* chooser surface live; codex
   ZERO findings.
7. **#205** `81b04bc` — lane heartbeat (the #194/#199/#204 fold,
   post-#204 counts).
8. **#208** `0e7cacd0` — btd6 resolver maps/modes matching: the first
   #144 parked DOMAIN item retires its oracle_cards ledger line
   (typed MapEntry/ModeEntry, the shipped `_match_terms` discipline
   incl. the common-word quirk, deterministic_answer's shipped
   precedence); zero manifest/golden/ratchet movement; codex
   zero-findings review at the final head (the lane's precedence-hijack
   question, comment 4948465613, drew only the boilerplate
   no-issues reply).

## Band-7 position at wrap-up (final counts)

Measured by the #208 worker at the merged tree `0e7cacd0` (local serial
ladder, real Postgres — trap 25): units **1458 passed / 2 skipped**;
gate **GREEN 258/258 across 37 ported**; report **295/467 green,
467/467 replayable, 37/49 ported**; corpus **467 = 465 imported + 2
minted** (#194's btd6_strategy_form_submit pair). The gate/report
movement 253→258 / 291→295 inside the #208 window is the parallel
parity lane's #207 (moderation/channel strays re-homed), not this
lane's slices — #199/#204/#208 minted zero goldens.

## Remaining map (for a fresh successor)

- **Parked domain items** (#144 ledger, next-smallest first): freeplay
  MOAB scaling (needs oracle `bloon_rbe_at_round` spawn-tree
  reconstruction), the boss estimator arm, the CT-team guided-set flow
  (NK-live-gated), the `!btd6 ops seed-data` terminals.
- **Kernel-band minted golden set** — #194's named follow-up (the
  A-16-clause-3 declined-P2 successor); would flip kernel.status.
- **CommandSpec modal facet** — the slash-opens-modal ingress (#194's
  ledgered deviation; the golden-pinned prefix pointer byte stays).
- **Review-channel poster** — parks with NL arming.
- **Live-NL leg** — BLOCKED on OWNER-ACTION 5 (`ANTHROPIC_API_KEY` +
  `AI_ENABLED` absent from the session env; unchanged since #151's
  live drive).
- **Testing-report row 9** (band 7) — pending the band's own
  live-testing pass (the band-6 row-8 convention).
- **Oracle maps/modes DB grounding** (`btd6_facts` pass) + the
  `!btd6 map|mode` command surfaces (no corpus capture exists — trap-28
  check in the #208 card) — ride D-0046.

## Honest notes (ledgered oddities)

- **Pre-existing latent bug, ledgered not fixed**:
  `sb/domain/btd6/service.py::_run_op` reads `result.ok` / flat
  `result.after` — unreachable via golden-driven lanes; guard recipe in
  `.sessions/2026-07-11-modal-vocabulary-btd6-strategy-form.md`.
- **`owner-ask-wall-unrecorded` advisory** (surfaced by #199's strict
  check): the OWNER-ACTION 3 ruleset wall was not in
  docs/CAPABILITIES.md — CLOSED by this wrap-up PR's append-log entry
  (the checker's own mechanical recipe).
- **Codex calibration**: line-anchored findings stayed REAL all session
  (3/4 fixed in-PR at #187 + 1 verified-declined, 1 verified-declined
  with doctrine citation at #194, 3/3 verified-and-fixed at #199, zero
  findings at #204 and #208); top-level claims (commits/PRs codex says
  it made) remain phantom-prone — Q-0120 verification stayed mandatory;
  one usage-limit window mid-evening recovered within the window.
- **Oracle default-branch churn (trap 24)**: moved repeatedly across
  the session — …→a03e5fe8 (#185) →a409d9b7 (#187) →8214200a (#194)
  →2c7d2de7 (#204) →d647b2e9→7349c8a7 (#208); a post-#208 probe
  reported `b2b7fe0c` (carried as reported — the oracle repo is outside
  this wrap-up seat's repo scope, so that last head is not
  re-verified). The corpus pin stays `7f7628e1`; every slice diffed
  fragments against goldens FIRST.
- **The #199 splice retired a standing workaround**: flip PRs no longer
  run the run-learn-restore-hand-apply `--write-ratchet` dance —
  `--write-ratchet` at the final head is a byte-level no-op on a clean
  tree.

## Verification

All 8 merge shas verified against `git log origin/main` at `0e7cacd0`;
all 8 PRs confirmed `merged: true` via the GitHub API at wrap-up; no
open PRs and no stray remote branches from this lane (the two open
codex doc-review PRs #196/#206 and the band-1 heartbeat branch are
other actors'); control/claims/ holds no claim files — nothing
dangles. Final counts read from the #208 PR body (the worker's
at-merged-tree ladder), not carried forward. `bootstrap.py check
--strict` green at the wrap-up head with the advisory closed.

## 💡 Session idea

The parked-item retirement loop is now a reusable recipe (D-0071/72/74,
#208): grep the deviation ledger for the item's own sentence, port,
retire the sentence in the same diff. The next successor should apply
it to freeplay MOAB scaling — but note that item is NOT self-contained
like maps/modes: `bloon_rbe_at_round` needs the oracle's spawn-tree
walk reconstructed, so budget a full trap-24 fragment pass before
writing code. If corpus leverage matters more than domain breadth, the
kernel-band minted golden set is the higher-value pick — it flips
kernel.status and exercises the #194 minting pipeline a second time,
hardening the A-16-clause-3 strip doctrine into a template.

## ⟲ Previous-session review

(Covers the #181 wrap-up lane, `.sessions/2026-07-11-band7-builder-session.md`.)
Its remaining map was ACCURATE and this continuation consumed it in
order: behavior-preset + orchestration-mutation (landed #185/#187),
the D-0066 successors (landed #194), the #144 domain list (first item
landed #208); review-channel poster / live-NL / testing row 9 stand
exactly as it parked them. Its session idea called the fork right —
(a) behavior-preset first was what happened — but overstated the
D-0066 successor's reach: it predicted the modal vocabulary would
delete exemptions across TWO reason classes; #194 deleted only the
btd6 `modal-driven` row (the six ai rows still ride the class, and
`select-driven` was untouched). Two real omissions: its map did not
carry the two hygiene items (write-ratchet comment destruction, the
ai-dir conftest scatter) — they lived only in the #144 ledger and had
to be re-surfaced at the #192 heartbeat — and it left the
`_KNOWN_ENSURE_ONLY`=45 hand-count as a band-boundary fact where this
continuation never needed it. Its verification discipline (counts from
CI logs, shas from origin/main) transferred verbatim and is what this
card mimics.

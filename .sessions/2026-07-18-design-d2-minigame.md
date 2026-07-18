# 2026-07-18 — D2 real-time minigame framework design doc

> **Status:** `complete`

- **📊 Model:** opus-4.8 · medium · docs · D2 real-time minigame framework design doc (born-red, holds substrate-gate)

## Scope

The 2026-07-18 planning phase turns the D1–D6 forward lanes into fuller design docs
the owner reacts to and prioritizes (the completeness-reconciliation snapshot,
`docs/status/completeness-table-2026-07-18.md`, #525; D4 opened the series in #528).
This slice is the **D2 real-time minigame framework** design doc: the fishing
subsystem already ships a real-time minigame (the D-0043 bite/reel timing gate)
deterministically on the logical clock — this doc designs GENERALIZING that proven
pattern into a reusable primitive other minigames can build on.

It is a docs-only planning artifact — no `sb/` code changes. The design doc is
grounded evidence-first in the ACTUAL fishing real-time surfaces read this session
(`sb/domain/fishing/{service,minigame}.py`, `sb/kernel/panels/{timers,engine}.py`,
`docs/decisions.md` D-0090), with `file:line` citations at HEAD `b39a37f`.

## Deliver

- `docs/design/D2-realtime-minigame-framework.md` — the fuller design doc: Problem
  (each real-time minigame hand-rolls timers + logical-clock enforcement; fishing
  proved the pattern but it is not reusable), The proven pattern (arm-window → live
  cues via one-shot timers + session refresh → resolve by logical-clock timestamp
  math → deterministic/mintable enforcement, citing the exact fishing symbols),
  Proposed framework (a kernel-level minigame primitive: window/state machine, timer
  arming, logical-clock resolution, deterministic replay for goldens; the API a new
  minigame implements, respecting layer rules — kernel primitive, per-game logic in
  `sb/domain/<key>`, no kernel→domain edge), Affected surfaces / candidate consumers,
  Rough size (S/M/L + slicing, prefer additive extraction fishing later adopts),
  Open questions for the owner. `> **Status:** \`plan\`` badge (a valid docs-gate token).
- `docs/design/README.md` — the D2 index row flips from `planned` to a link to the
  new doc (docs-gate orphan check); no other row touched.

## Verification

- `python3 bootstrap.py check --strict` → 0 exit-affecting findings (badge valid +
  the new doc reachable from the index); the only red in CI is this card's own
  designed born-red hold on the substrate-gate until the card flips complete.
- No `sb/` or test code touched — docs-only; the functional CI gates ride green,
  substrate-gate is the expected sole hold.

## 💡 Session idea

The load-bearing finding of the grounding pass: fishing's real-time minigame is
already a **two-plane** design that is generalizable almost verbatim. The COSMETIC
plane (live bite/nibble/got-away cues) rides the D-0090 one-shot timers
(`sb/kernel/panels/timers.py`) + `push_session_refresh`
(`sb/kernel/panels/engine.py:541`) and is allowed to no-op headlessly
(`EDIT_UNAVAILABLE`); the ENFORCEMENT plane is pure timestamp math on the logical
clock (`minigame.reel_is_in_time` over `SYSTEM_CLOCK`, `sb/domain/fishing/minigame.py:202`)
and NEVER rides the timers. That split is exactly why fishing is deterministic and
mintable under the parity harness. The reusable primitive is that split made
first-class — a kernel window/state-machine that owns the timer arming + identity
staleness guards + due-guard (`_timer_due`, `service.py:131`), leaving each game to
supply only its pure roll/resolve leaves and its cue copy. The refactor risk is real
(fishing's timing goldens are byte-pinned), so the doc argues for ADDITIVE extraction:
build the primitive, prove it on a NEW second minigame, let fishing adopt it later as
a byte-identical internal swap rather than a big-bang rewrite of the reference impl.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-design-d4-observability.md` (#528), the first doc of
this planning-mode series. This card mirrors its shape exactly: a docs-only,
born-red, substrate-gate-holding design doc grounded evidence-first with `file:line`
citations, flipping one `docs/design/README.md` index row from `planned` to a link.
D4's recurring theme — the grammar/spec leaves are richer than the live wiring, so
the planning docs are mostly about ARMING what exists — carries here in a sharper
form: the real-time SEAMS (one-shot timers, push-edit, logical-clock enforcement)
already exist and are proven by fishing; D2 is about lifting the ORCHESTRATION that
currently lives inline in one domain module into a reusable kernel primitive, not
inventing new machinery.

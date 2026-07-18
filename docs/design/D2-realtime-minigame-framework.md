# D2 — Real-time minigame framework

> **Status:** `plan`
>
> A forward design proposal from the 2026-07-18 planning phase, opened per the
> completeness snapshot's recommendation to turn the D1–D6 lanes into fuller
> design docs (`docs/status/completeness-table-2026-07-18.md`). This is a PLAN,
> not built work — the owner reacts and prioritizes; the code and
> `docs/decisions.md` win once slices land. Evidence citations are `file:line`
> at HEAD `b39a37f` unless noted.

## TL;DR

The fishing subsystem already ships a **working, deterministic, mintable
real-time minigame** — the fishing `cast → wait → BITE → reel` timing gate
(`docs/decisions.md` D-0090). It is built from two kernel seams that are
already generic — the one-shot timer (`sb/kernel/panels/timers.py`) and the
session push-edit (`push_session_refresh`, `sb/kernel/panels/engine.py:541`) —
plus a **two-plane discipline** that lives, today, entirely inline in one
domain module (`sb/domain/fishing/service.py`): a **cosmetic plane** (live
cues that may no-op headlessly) rides the timers, and an **enforcement plane**
(pure timestamp math on the logical clock) never does. That split is exactly
why the minigame replays byte-for-byte under the parity harness while still
feeling live in production.

The problem this doc frames: the split is **proven but not reusable**. A
second real-time minigame would re-derive the same ~250 lines of timer arming,
identity/staleness guards, due-guarding, and pop/sweep bookkeeping by hand —
the subtle, easy-to-get-wrong part — while the genuinely game-specific code
(the roll and the resolve) is a handful of pure functions. This doc proposes
lifting the orchestration into a **kernel-level minigame primitive** that owns
the timers + guards + logical-clock resolution, and defines the small API a
new minigame implements. It argues for **additive extraction**: build the
primitive, prove it on a new minigame, and let fishing adopt it later as a
byte-identical internal swap rather than a risky rewrite of the reference impl.

## Problem

Real-time minigames — timing/reaction mechanics that unfold over seconds on a
live Discord message — are high-value engagement surfaces, and the platform
already has the hard parts solved once. But the pattern is **captured in a
single domain module**, so every new one pays the full re-implementation cost.

### P1 — The reusable orchestration is hand-rolled inline in fishing

Everything below lives in `sb/domain/fishing/service.py` and is generic in
shape, fishing-specific only in copy and in which pure function it calls:

- **Timer arming as background cues.** `_arm_bite_timers`
  (`service.py:213-278`) schedules three one-shot timers — a fake-out nibble,
  the `🐟 BITE!` arm at `bite_at`, and an unprompted got-away at
  `bite_at + window` — each via `timers.schedule(...)`
  (`service.py:271-277`). `_arm_fight_timers` (`service.py:281-324`) does the
  same for each reel-fight round (arm + expiry).
- **Identity / staleness guards.** Every callback re-checks that the parked
  entry is still the one it was armed for before acting — `if
  _PENDING_CASTS.get(key) is not entry ... return` (`service.py:240,247,255`)
  and the fight-round `_stale()` closure keyed on `taps_done`
  (`service.py:298-301`). This is the oracle's `_round_id` staleness token,
  re-expressed by hand.
- **The due-guard bridging wall time to logical time.** `_timer_due`
  (`service.py:131-143`) gates every callback on
  `SYSTEM_CLOCK().timestamp() >= fire_at_f - 0.05` so a wall-fired timer whose
  *logical* moment has not arrived (exactly what happens inside a parity case,
  where the logical clock only advances when a step drives it) is a no-op.
- **Pop / cancel / sweep bookkeeping.** `_cancel_cast_timers`
  (`service.py:124-128`) disarms an entry's timers idempotently at every
  resolve/sweep/pop site; `_sweep_expired_casts` (`service.py:360-368`) drops
  entries past the outer timeout; `reset_pending_casts_for_tests`
  (`service.py:371-376`) is the per-case state reset the parity harness calls.

None of this is about fish. It is the *machinery of a windowed real-time
round*. A second minigame re-writes all of it — and the guards are precisely
the parts whose absence would silently break determinism (a missing
`_timer_due` check pops a round the goldens still own; a missing staleness
guard false-fails a replaced round).

### P2 — The enforcement/cosmetic split is a discipline, not a structure

The property that makes fishing mintable is that **enforcement never rides the
timers**. Resolution is pure timestamp math on the logical clock:
`minigame.reel_is_in_time(now_f - bite_at_f, reaction_window)` over
`SYSTEM_CLOCK()` in the Reel handler (`service.py:888-891`,
`minigame.reel_is_in_time` at `sb/domain/fishing/minigame.py:202-205`), while
the timers only push *cosmetic* edits that are allowed to no-op headlessly via
`EDIT_UNAVAILABLE` (`push_session_refresh`, `engine.py:559-560`). The
docstrings shout this rule repeatedly ("Enforcement itself NEVER rides these
timers — it is timestamp math on SYSTEM_CLOCK", `service.py:229`) because it is
enforced only by author discipline. A new minigame that accidentally lets a
timer callback perform the authoritative resolve would pass every headless test
(the timer never fires in parity) and then diverge in production — a
determinism bug that CI cannot catch. The split wants to be a **structural
guarantee of the primitive**, not a convention each game must remember.

### P3 — The seams exist; the orchestration layer above them is missing

The two kernel seams are already clean, generic, and layer-correct — the
one-shot timer (`sb/kernel/panels/timers.py:58-79`) and the push-edit
(`engine.py:541-584`), minted together under D-0090 "beside their only
consumer seam ... giving the next real-time surface a sanctioned home". But
they are *primitives one layer too low*: they schedule a callback and edit a
message. The layer that turns them into a *minigame* — a window with a state
machine, a resolution verdict, and replay determinism — does not exist as a
reusable unit. Fishing is currently both the only consumer AND the de-facto
(uncodified) framework. Grep confirms it: the only importers of
`sb.kernel.panels.timers` in `sb/` are the timer module itself and
`sb/domain/fishing/service.py`.

### P4 — Cost of re-implementing per game

Concretely, a second minigame today re-derives: the pending-entry registry +
its TOCTOU-safe reservation (`service.py:494-512`), three-to-five timer
arms with per-callback identity + due guards, the pop/restore-on-failure dance
(`service.py:918-934`), the outer sweep, and the per-case reset hook — roughly
the 250 lines from `service.py:112` to `:376` — before writing a single line of
its actual game. The parts it *should* only need to write are the pure rolls
(`roll_bite_delay`, `roll_fakeout`, `roll_escape`) and the pure verdict
(`reel_is_in_time`) — a few dozen lines in `sb/domain/fishing/minigame.py`.
The ratio is inverted: the boilerplate dwarfs the game, and the boilerplate is
the part that must be *exactly right* for determinism.

## The proven pattern (from fishing)

Extracted from the working fishing minigame, the reusable shape is a
four-stage loop. Each stage cites the fishing symbol that implements it today.

1. **Arm the window.** At the triggering action, roll the game's timing from a
   runner-armable RNG and park a state entry, then open the live panel. Fishing:
   `cast_open` rolls `bite_delay = minigame.roll_bite_delay(ops_mod.cast_rng(), ...)`
   (`service.py:606-611`) on the module's private, test-armable RNG
   (`ops.cast_rng()`, `sb/domain/fishing/ops.py:120-124`), parks the entry with
   its float timestamps `cast_at_f` / `bite_at_f` / `reaction_window`
   (`service.py:648-672`), opens the panel, and arms cues via
   `_arm_bite_timers` (`service.py:709`).

2. **Live cues via one-shot timers + session refresh.** Background timers push
   *cosmetic-only* state onto the live message. Fishing: `timers.schedule(...)`
   for nibble/bite/got-away (`service.py:271-277`), each firing
   `_push_cast_edit → push_session_refresh` (`service.py:146-172`,
   `engine.py:541`). These edits are allowed to no-op: no editor installed ⇒
   `EDIT_UNAVAILABLE` (`engine.py:559-560`), gone session ⇒ `EDIT_MISSING`
   (`engine.py:562-565`). Every callback is **identity-guarded** (stale entry ⇒
   return, `service.py:240,247,255`) and **due-guarded** on the logical clock
   (`_timer_due`, `service.py:131-143`).

3. **Resolve by logical-clock timestamp math.** The authoritative verdict is a
   pure comparison of `SYSTEM_CLOCK()` timestamps — never the timers. Fishing:
   the Reel handler computes `now_f = SYSTEM_CLOCK().timestamp()`
   (`service.py:770`) and decides in/late with
   `minigame.reel_is_in_time(now_f - bite_at_f, reaction_window)`
   (`service.py:888-891`; the fight-round twin at `:813-815`). Before-bite,
   in-window, and after-window are three timestamp branches
   (`service.py:860-916`).

4. **Deterministic / mintable enforcement.** Because (3) is pure timestamp math
   on the logical clock and (2) is cosmetic and no-ops headlessly, the whole
   minigame replays identically under the parity harness: the harness arms the
   same timers (whose wall delays never elapse inside a logical-clock case and
   whose edits no-op) while the same timestamps drive the same in/late verdicts.
   The RNG is runner-armed (`ops.set_rng_for_tests`,
   `sb/domain/fishing/ops.py:115-117`) so the timing rolls pin too, and the
   per-case reset (`reset_pending_casts_for_tests`, `service.py:371-376`)
   clears state between goldens. This is the D-0090 ruling's core guarantee.

The one-sentence shape: **arm-window → cosmetic cues on timers (no-op-safe) →
authoritative resolve on logical-clock timestamps → deterministic replay.**

## Proposed framework

A **kernel-level minigame primitive** in the K8 panels band, beside the seams
it composes (`sb/kernel/panels/timers.py` + the push-edit in
`engine.py`), that owns the orchestration (stages 1–2 machinery + the stage-3
resolution *harness*) and calls back into per-game *pure* leaves for the rolls
and the verdict. Respecting the layer rules (`.claude/CLAUDE.md`): the
primitive is kernel and imports **no domain**; each game lives in
`sb/domain/<key>` and *calls* the primitive — no kernel→domain edge, exactly as
D-0090 kept it ("Kernel imports no domain — the domain calls the engine").

### F1 — A windowed-round state machine + registry (new kernel leaf)

A new `sb/kernel/panels/minigame.py` (K8, importable by any domain) offering a
`RealtimeRound` primitive that internalizes the generic bookkeeping fishing
hand-rolls:

- **The parked-entry registry with a TOCTOU-safe reservation** — the
  reserve-before-first-await pattern (`service.py:494-512`) generalized, keyed
  by `(actor, guild, game_key)`, with a per-cast identity **token**
  (`service.py:349-357`) so a stale click/timer can only ever resolve its own
  round.
- **Timer arming from a declarative cue schedule** — the caller passes a list
  of `(delay_s, cue)` and terminal `(window_s → expiry)` beats; the primitive
  wraps each in the identity guard + the `_timer_due` logical-clock due-guard
  (`service.py:131-143`) automatically, so a game **cannot** forget them.
- **Cancel/sweep/reset built in** — `_cancel_cast_timers` (`service.py:124`),
  `_sweep_expired_casts` (`service.py:360`), and the per-case reset
  (`service.py:371`) become primitive methods, so the parity harness gets one
  reset hook per game for free.

### F2 — Structural enforcement/cosmetic split (the P2 guarantee)

The primitive exposes **two distinct call surfaces** so the split is
structural, not disciplinary:

- **Cue callbacks** may only push through the primitive's cosmetic channel
  (wrapping `push_session_refresh`) — they return nothing authoritative and
  their no-op outcomes (`EDIT_UNAVAILABLE`/`EDIT_MISSING`) are swallowed by the
  primitive.
- **The resolve entrypoint** — called from the interaction handler at click
  time — receives `elapsed = SYSTEM_CLOCK() − round.armed_at` and the game's
  pure verdict function, and returns an in-window / early / late verdict. It
  never touches a timer. A game physically cannot make enforcement ride a timer
  because the timer surface has no resolve capability. This turns the
  repeated-docstring rule (`service.py:229`) into a type-level guarantee.

### F3 — The per-game API surface (what a new minigame implements)

A new minigame supplies only pure, stdlib-only leaves in its own
`sb/domain/<key>/` — the fishing `minigame.py` is the template (pure + no
Discord/DB/clock, `sb/domain/fishing/minigame.py:28`):

- **`roll_timing(rng) -> RoundTiming`** — the window open delay + reaction
  window (fishing: `roll_bite_delay`, `minigame.py:94-110`), drawn on a
  runner-armable RNG (the `cast_rng()` seam, `ops.py:120-124`).
- **`resolve(elapsed, window) -> Verdict`** — the pure in-window predicate
  (fishing: `reel_is_in_time`, `minigame.py:202-205`), optionally a
  multi-stage ladder (fishing's early/in/late + fight rounds).
- **cue copy + optional multi-round state** — the strings the cosmetic channel
  pushes, and (for fishing's reel-fight) a re-arm hook after each round
  (`FIGHT_INTER_ROUND_DELAY`, `minigame.py:88`; re-arm at `service.py:849-851`).
- **the terminal handlers** — what to commit on success (fishing routes to the
  audited `fishing.cast` op, `service.py:928`) and what copy to show on
  early/late/expiry.

The domain handler's body shrinks to: `round = RealtimeRound.arm(key,
timing=game.roll_timing(rng), cues=game.cues)`; then at click time `verdict =
round.resolve(game.resolve)` and branch. The ~250 lines of machinery become a
few calls.

### F4 — Deterministic replay for goldens (built into the primitive)

The primitive standardizes what fishing wired by hand: a runner-armed RNG hook
per game (like `set_rng_for_tests`, `ops.py:115-117`), the `_timer_due`
logical-clock due-guard on every cue (so wall timers never fire in-case), and a
single `reset()` the parity harness calls per case
(`reset_pending_casts_for_tests`, `service.py:371-376`). A new minigame gets
mintable goldens **for free** as long as its rolls go through the armed RNG and
its verdict is pure timestamp math — the primitive enforces the rest.

## Affected surfaces / candidate consumers

| Band | Work | Notes |
|---|---|---|
| kernel / panels | **new** `sb/kernel/panels/minigame.py` (`RealtimeRound` primitive + registry) | composes the existing `timers.py` + `push_session_refresh`; imports no domain |
| kernel / panels | `sb/kernel/panels/timers.py`, `engine.py:541` | unchanged — the primitive sits *above* them |
| domain (reference) | `sb/domain/fishing/{service,minigame}.py` | later ADOPTS the primitive as a byte-identical internal swap (not part of the first slice) |
| domain (new consumer) | a second minigame in `sb/domain/<key>/` | supplies only the pure `roll_timing`/`resolve` leaves + cue copy |

Candidate second consumers (skimmed this session):

- **A reflex/reaction casino game** — e.g. a "quick-draw" or "catch the number"
  timing bet in the casino/games surface. The casino section spec already
  exists (`docs/specs/casino-section-spec.md`, referenced from
  `docs/design/README.md`), and `sb/domain/games/` is the natural home; a
  timing-bet minigame is the most direct fit for arm-window → resolve-on-click.
- **A turn-timeout layer for the existing PvP games** — blackjack and rps run
  as panel sessions with a fixed `timeout_s` (blackjack `timeout_s=180`,
  `sb/domain/blackjack/panels.py:155,205`; rps `timeout_s=180/600`,
  `sb/domain/rps/panels.py:155,192`). These are *coarser* (a whole-turn clock,
  not a sub-second reflex), so they are a weaker fit for the reflex primitive
  but could reuse the same arm/expire/logical-clock-resolve spine for a live
  "your move — 30s left" countdown cue. Worth naming as a stretch consumer, not
  a first target.

The reflex-casino game is the recommended proving ground: new code (no existing
goldens to protect), squarely in the arm-window → resolve-on-click shape, and
it exercises the primitive end-to-end without touching the fishing reference
impl.

## Rough size + suggested slicing

- **D2.1 — extract the primitive (`RealtimeRound` in `sb/kernel/panels/minigame.py`)**
  — **M**. Lift the generic registry + reservation + timer-arming +
  identity/due guards + cancel/sweep/reset out of the fishing shape into a
  kernel leaf, with unit tests mirroring
  `tests/unit/panels/test_oneshot_timers.py` /
  `test_push_session_refresh.py`. No behavior change anywhere yet — pure
  addition. Land first, standalone.
- **D2.2 — prove it on a NEW minigame** — **M–L**. Build the reflex-casino
  minigame *on the primitive* (its pure `roll_timing`/`resolve` leaves + cue
  copy + terminals + goldens). This is the real validation: a mintable
  second real-time minigame with a fraction of fishing's boilerplate.
- **D2.3 — fishing adopts the primitive (OPTIONAL, later)** — **L**, and the
  riskiest. Swap fishing's inline machinery for the primitive as a
  **byte-identical internal refactor** — the fishing timing goldens
  (`goldens/fishing/*`, the retuned reel-write cases from D-0090) must replay
  unchanged, and the two-plane split must stay exact. **Prefer additive
  extraction**: do NOT rewrite fishing as part of D2.1/D2.2. Fishing stays the
  reference impl until the primitive is proven on a green second consumer;
  adoption is then a mechanical, golden-gated swap the owner can schedule
  independently (or decline — fishing working as-is is a valid end state).

Suggested landing order: **D2.1 → D2.2**, then **D2.3 only if/when the owner
wants fishing consolidated onto the shared primitive.** The risk of touching
the working fishing code is real (its determinism is byte-pinned across the
D-0090 goldens), so the design deliberately keeps the refactor of fishing
**out of the critical path**.

## Decision-ready refinement

> Added 2026-07-18 to make this proposal **decision-ready** — one owner
> go/no-go away from executable. Triages the six open questions below into
> **one** load-bearing owner call (routed to `docs/question-router.md`) and
> **five-and-a-half** mechanical shape decisions resolved here as flagged
> decide-and-flag defaults (PL-001) the owner can override with a word.

### The single owner call (routed, not decided here)

Every one of the six questions below *presupposes we are building the
primitive* — they are all shape questions. The load-bearing call sits **above**
them: **should the reusable primitive be built at all / now?** Today fishing is
the *only* real-time minigame, so the extracted primitive would ship with
exactly **one consumer**, and a reusable framework earns its keep at **≥2**.
This yes/no is genuine product intent (build-cost vs speculative-reuse) and is
routed to `docs/question-router.md` as an OPEN owner go/no-go —
**build now / defer until a 2nd real-time minigame needs it / never** — with a
recommended **DEFER-until-2nd-consumer** default. Rationale lives there; the
five-and-a-half defaults below apply *if/when* the answer is GO.

### Recommended framework shape (grounded in the fishing code it lifts)

The shape is already specified above (§ "Proposed framework", F1–F4); the
recommendation is to build it **exactly as F1–F4 describe** — no larger. The
reusable kernel leaf `sb/kernel/panels/minigame.py` exposes a `RealtimeRound`
primitive that lifts, verbatim in behaviour, the determinism-critical machinery
that is hand-rolled today in `sb/domain/fishing/service.py`:

- the parked-entry registry + TOCTOU-safe reservation + per-round identity
  token (`_next_cast_token`/`_cast_token_counter`, `service.py:349-357`);
- declarative cue-timer arming that **auto-wraps** each callback in the identity
  guard + the logical-clock due-guard (`_timer_due`, `service.py:131-143`) — the
  two guards a hand-rolled game most easily forgets (`_arm_bite_timers`,
  `service.py:213-278`; `_arm_fight_timers`, `service.py:281-324`);
- built-in cancel/sweep/reset (`_cancel_cast_timers` `service.py:124-128`,
  `_sweep_expired_casts` `service.py:360-368`, `reset_pending_casts_for_tests`
  `service.py:371-376`);
- a **two-surface** call shape making the enforcement/cosmetic split structural
  (cue callbacks reach only the cosmetic `push_session_refresh` channel; the
  resolve entrypoint is the only path that returns a verdict and never touches a
  timer — F2).

A new game supplies only the pure, stdlib-only leaves that
`sb/domain/fishing/minigame.py` is the template for: `roll_timing` (fishing's
`roll_bite_delay`, `minigame.py:94-110`, on the runner-armable `cast_rng()`
seam, `ops.py:115-124`) and `resolve` (fishing's `reel_is_in_time`,
`minigame.py:202-205`) plus cue copy and terminal handlers. **The two kernel
seams it composes stay unchanged** — the one-shot timer
(`sb/kernel/panels/timers.py:58-79`) and the push-edit (`engine.py:541-584`),
both minted under the D-0090 ruling.

### The five-and-a-half shape defaults (decide-and-flag — owner may override any)

| # | Shape question | **Flagged default** | Override lever |
|---|---|---|---|
| Q1 | Proving ground for D2.2 | A **reflex/timing casino minigame** in `sb/domain/games/` — new code, no goldens to protect, squarely arm-window → resolve-on-click; it validates the API end-to-end without touching fishing. | Owner names a specific roadmap minigame to design the API against instead. |
| Q2 (shape half) | Fishing adoption timing | **Leave fishing as the reference impl**; D2.3 (fishing adopts the primitive) stays OPTIONAL, out of the critical path, and only ever as a byte-identical golden-gated swap. "Fishing is the reference, new games use the primitive" is an acceptable **permanent** end state. | Owner schedules the golden-gated swap once the primitive is proven green elsewhere. *(The "eventually consolidate fishing y/n?" preference stays flagged to the owner — the half-question.)* |
| Q3 | Window / refresh budget | Expose the reaction window as a **per-game knob** AND carry a **platform-wide floor** (inherit fishing's `REACTION_WINDOW = 2.5`, `minigame.py:64`) so no game ships an unwinnable sub-second window; default the live-cue **edit ceiling** to fishing's proven ~3-per-round budget (`service.py:271-277`). | Owner lifts/lowers the floor or the per-round edit cap. |
| Q4 | Multi-round vs single-shot | Ship **single-shot first-class**; model multi-round via a **re-arm hook** (the fishing fight-round pattern, `_arm_fight_timers` + re-arm at `service.py:849-851`) rather than a full round-sequence abstraction, until a consumer needs the richer model. | The proving-ground game needs native multi-round → build the sequence abstraction in D2.2. |
| Q5 | Band home | **`sb/kernel/panels/minigame.py`** (K8 panels band, beside the seams it composes) — matches where D-0090 minted the seams "beside their only consumer", lowest friction, layer-safe (kernel imports no domain). | Promote to a dedicated `sb/kernel/minigame/` band once a 2nd panels-adjacent seam accretes. |
| Q6 | Turn-timeout consumers (blackjack/rps) | **Out of scope.** Keep the primitive focused on the sub-second reflex shape; leave whole-turn timeouts on the existing panel `timeout_s` mechanism (`blackjack/panels.py:155,205`, `rps/panels.py:155,192`). Name them a stretch consumer only. | Extend the arm/expire/logical-clock spine to a "N seconds left on your move" countdown cue later. |

### What building it costs, and what it unblocks

- **Cost:** D2.1 (**M**) is a *pure addition* — lift the ~250 lines of generic
  machinery (`service.py:112-376`) into the kernel leaf with unit tests
  mirroring `tests/unit/panels/test_oneshot_timers.py` /
  `test_push_session_refresh.py`; **zero behaviour change anywhere** (fishing is
  not touched). D2.2 (**M–L**) builds the proving-ground game on it.
- **Unblocks:** every future real-time minigame writes only its pure
  `roll_timing`/`resolve` leaves + cue copy (a few dozen lines) instead of
  re-deriving the determinism-critical boilerplate by hand — and gets **mintable
  goldens for free** (the primitive owns the armed-RNG hook, the due-guard, and
  the per-case reset). The inversion P4 describes (boilerplate dwarfs the game,
  and the boilerplate is the part that must be *exactly* right) is retired.
- **Refactors onto it:** exactly **one existing** minigame — fishing — and only
  optionally (D2.3, byte-gated, owner-scheduled). **Zero** other existing
  consumers today: that one-consumer fact is precisely why the go/no-go leans
  DEFER.

## Open questions for the owner

> **Decision-ready status (2026-07-18):** the six questions below are now
> triaged in § "Decision-ready refinement" above. Q1 and Q3–Q6 (and the shape
> half of Q2) are resolved as **flagged decide-and-flag defaults** the owner can
> override; the single load-bearing call that sits above all six — *build the
> reusable primitive now vs defer vs never* — is routed to
> `docs/question-router.md`. The originals are kept verbatim below for
> provenance.

1. **Which games to target first?** Is a reflex/timing casino minigame the
   right proving ground for D2.2, or is there a specific minigame on the roadmap
   (a new standalone game, a fishing-adjacent mechanic) that should drive the
   primitive's API shape instead? The API is best designed against a real second
   consumer, not in the abstract.
2. **Refactor fishing onto it now, or leave it as the reference impl?** The doc
   recommends leaving fishing untouched until the primitive is proven elsewhere
   (D2.3 optional/later) to avoid risking the byte-pinned timing goldens. Does
   the owner want fishing consolidated onto the shared primitive eventually, or
   is "fishing is the reference, new games use the primitive" an acceptable
   permanent state?
3. **Latency / refresh budget.** The reaction window is deliberately generous
   (`REACTION_WINDOW = 2.5`, `sb/domain/fishing/minigame.py:64`) because a
   Discord round trip makes a window "a presence check, not a reflex test"
   (`minigame.py:9-11`). Should the primitive expose the window as a
   per-game knob only, or also carry a platform-wide floor so no game ships an
   unwinnable sub-second window? How many live cue edits per round is the
   budget (fishing pushes up to ~3 per bite round + one per fight round —
   `service.py:271-277,319-323`) before Discord edit rate limits bite?
4. **Multi-round vs single-shot as first-class.** Fishing has both a single
   bite gate and a multi-round reel-fight (`_arm_fight_timers`,
   `service.py:281-324`). Should the primitive model multi-round natively (a
   round sequence with re-arm hooks), or ship single-shot first and add
   round-sequences when a consumer needs them?
5. **Where does the primitive live — panels band or a new `sb/kernel/minigame/`
   band?** It composes the K8 panels seams (timers + push-edit), so
   `sb/kernel/panels/minigame.py` is the lowest-friction home (matches where
   D-0090 minted the seams "beside their only consumer"). A dedicated band is
   cleaner long-term but heavier. Which does the owner prefer?
6. **Turn-timeout consumers (blackjack/rps) in scope?** These are coarser
   whole-turn clocks (`timeout_s=180/600`), not sub-second reflex gates. Should
   the primitive stretch to cover a live "N seconds left on your move" countdown
   cue for them, or stay focused on the reflex/timing shape and leave
   turn-timeouts to the existing panel `timeout_s` mechanism?

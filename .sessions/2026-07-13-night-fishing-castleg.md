# 2026-07-13 — night verify: fishing cast-leg profile wiring (ORDER 019 item 4)

> **Status:** `in-progress`

- **📊 Model:** `Claude Fable` · NIGHT-RUN verify-first slice · mandate:
  ORDER 019 item 4 — verify the venue/rod/bait/structure→cast wiring
  claim (#373, goldens #387, claim closed #389) against HEAD, then true
  up the stale completeness-table row if the code confirms.

## Scope

VERIFY-FIRST: read the cast outcome path at HEAD (`begin_cast` port
`fishing.cast_open` → `roll_catch` → `fishing.record_cast` commit) and
confirm every profile input — venue, rod, bait, gear, structure,
weather — actually drives a cast outcome, excluding only the parked
D-0043 real-time bite-timing rung (knobs computed + surfaced but never
gating, per the service PENDING-roster note,
`sb/domain/fishing/service.py:1032`).

Expected finding (confirmed): the wiring is LIVE and shipped — the
deliverable is DONE-ALREADY plus a small doc true-up: the fishing row
(line 76) and Top-gaps item 1 of
`docs/status/completeness-table-2026-07-13.md` still claim "the cast
leg still runs the starter shore profile", contradicting the merged
#373 state.

## Verification (citation bundle)

All at HEAD `0d932a2` (main):

- **venue** — read `service.py:231-232`; drives the species pool
  (`roll_catch(..., venue=profile.key)` `service.py:283-284` →
  `ops.py:126` → `catalog.unlocked_species` venue filter
  `catalog.py:101-104`), the quiet-venue guard `service.py:285-290`,
  and rides the parked entry (`service.py:321`) into the commit where
  it gates the deepwater-only coral drop (`ops.py:216,243` →
  `roll_coral_drop`/`coral_drop_chance` `ops.py:164-185`).
- **rod** — read `service.py:229-230`; `rod.rarity_pull` compounds into
  `effective_pull` (`service.py:260-266`) → the roll's weight exponent
  (`ops.py:130-131`).
- **bait** — read `service.py:236-239`; `bait.rarity_pull` in
  `effective_pull` (`service.py:263`); one charge spent per cast via
  `store.consume_bait_charge` (`service.py:311-315`).
- **gear** — read `service.py:241-245`; `gear_pull` in `effective_pull`
  (`service.py:265`).
- **weather** — read `service.py:233`; `weather.rarity_mult` in
  `effective_pull` (`service.py:264`).
- **structures** — one read `service.py:213`: Tide Pool pull mult
  (`service.py:247-249` → `:265`), Boathouse regen mult gating the
  energy settle/wait (`service.py:214-228`), Fishery
  `double_catch_chance` (`service.py:253-256`) riding the parked entry
  (`service.py:322`) into the commit's bonus roll (`ops.py:217-218,240`).
- **Parked (out of scope, D-0043)** — the bite-speed knobs
  (rod/bait/weather/gear/Dock) compound into `effective_bite_speed`
  (`service.py:267-273`) but are deliberately outcome-inert
  (`service.py:332-335`, `del effective_bite_speed`) pending the
  real-time minigame rung — exactly as the roster note ledgers.
- **Goldens (#373/#387)** — `parity/goldens/fishing/
  fishing_cast_reel_write.json`, `fishing_cast_deepwater_reel_write.json`,
  `fishing_cast_bait_spend_write.json` present at HEAD.
- **Tests** — `python3 -m pytest tests/ -q -k fishing`: 77 passed,
  2 skipped.

## What shipped

Doc true-up only (no code change needed): the fishing row (L76) and
Top-gaps item 1 (~L134-143) of
`docs/status/completeness-table-2026-07-13.md` now state the accurate
post-#373 state — venue/rod/bait/gear/structure/weather → cast wiring
LIVE (#373, write goldens #387, claim closed #389); the surviving parked
residue is the D-0043 real-time minigame rung (bite-delay/fake-out/
reel-fight timing — knobs computed + surfaced but not gating) + the
`_FishingDoneView` Cast-again continuation, per the service roster note.
The #410 how-to-fish content in the row is preserved.

Decide-and-flag adjacency: the completeness-remainders claim also
touches this file — disjoint rows, coordinated by claim scope.

## 💡 Session idea

This slice exists because a point-in-time status table went stale the
moment #373 merged — the same doc says "Regenerate rather than amend"
yet has now absorbed three hand-trued amendments (morning, evening, and
this night true-up). A tiny checker rule — every completeness-table
claim that cites a `PENDING`/roster note must quote its file:line, and
the checker greps that the cited line still says what the claim says —
would turn this whole verify-then-true-up class into a red gate instead
of a night order. The fishing row is the second row (after cleanup) to
need the same manual reconciliation in one day.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-rework-server-management-name-pair.md`.)
A model card for a decide-and-flag lane: the shape-A-over-B call is
argued from an existing shipped mechanism (the G-6 BOTH fold) rather
than schema growth, the verification block quotes exact counts (2428
passed, 484 goldens, roster 51→50), and the guard recipe names the two
sibling dirs the same mechanism would fix. Two small dings: its Model
line writes `fable-5` where the working agreement's cards standardized
on the family-level name, and the 💡 idea (the three-place attribution
checker) overlaps the guard-recipe paragraph enough that one of them
could have been a pointer. The friction footnote (`git mv` leaves a
dir husk that reds roster tests) is exactly the kind of trail note
HANDOFF.md exists for — it earned its length.

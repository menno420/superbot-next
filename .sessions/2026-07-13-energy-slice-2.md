# 2026-07-13 — mining energy slice 2: wire !cook/!use + argful goldens

> **Status:** `complete`

- **📊 Model:** `fable-5` · energy-lane slice 2 (cook/use terminals) ·
  stacked on #384 `claude/energy-slice-1` (itself on #320
  `mining/energy-domain-core`) per ORDER 017 rule 2 (branch from an open
  PR's head, note the base in the PR body).

## Scope

Slice 2 of the energy lane per `docs/scoping/energy-system-scope.md`
(slice plan, "Slice 2 — wire `!use` + `!cook` terminals + argful
goldens"):

1. `sb/domain/mining/service.py` — `cook_route`/`use_route` argful
   BLOCKED→LIVE (bare usage guards stay byte-identical; success replies
   carry the shipped `<@u> ` mention prefix, refusals stay plain — the
   oracle cog contract).
2. `sb/domain/mining/ops.py` — `mining.cook` (one-txn fish-debit +
   cooked-fish-grant behind the campfire gate) and `mining.use`
   (one-txn item-debit + energy restore for food/boosters; torch /
   dynamite / generic flavour otherwise) over the slice-1
   `get_energy`/`set_energy` store pair + the #320 pure energy core.
3. Manifest: PENDING-roster comment truth-up (`cook`/`use` argful lanes
   leave the deferred list) + `manifest.snapshot.json` regen (the two
   new workflow refs; no new command rows).
4. Goldens (canonical D-0073 `capture_case` procedure, NOT hand-written):
   `!use ration` restore, `!use ration` when-full refusal,
   `!cook minnow` with campfire, `!use torch` flavour. Bare
   `sweep_cook`/`sweep_use` stay green.

Oracle copy source: `disbot/services/mining_workflow.py` `use_item` /
`cook` + `disbot/cogs/mining_cog.py` `use`/`cook` @
`87bbe1dbf0c504d1ef1fc9db466224303f16afba` (local clone, never MCP).

NOT this slice: no `!fastmine` dig-energy gating (slice 3 — owner-gated
Option A, sequenced after WP-3 #317), no migration (0052 landed in
slice 1), no new store rows.

## What shipped

All four scope items, PR #385 (opened stacked on #384 per ORDER 017
rule 2; #320 + #384 merged to main MID-SESSION — e902b0d, dc0e73d — so
GitHub auto-retargeted the PR to base `main`, correct and kept):

- `sb/domain/mining/ops.py` — `mining.record_use_item` /
  `mining.record_cook` one-txn legs + `USE_ITEM`/`COOK` CompoundOpSpecs
  (verbs `mining_item_used`/`mining_cooked`), `_rest_from` (consume-rest
  arg, digits kept), public `is_fish` (fishing-SPECIES seam),
  `COOKED_FISH`. Oracle copy verbatim (`mining_workflow.use_item`/`cook`
  @ 87bbe1d); the legs re-check guards in-txn — a race fence the oracle
  lacks (its raced cook dupes via the floor-0 debit; the port refuses).
- `sb/domain/mining/service.py` — `cook_route`/`use_route` argful
  BLOCKED→LIVE; refusal guards run as PRE-TXN pure reads in the routes
  so the bytes stay oracle-plain (in-leg ValidatorError wraps as the
  kernel envelope — caught when the first refusal capture pinned the
  wrapped byte); success prefixes the invoker mention. Bare usage guards
  byte-identical (`sweep_cook`/`sweep_use` stay green).
- Goldens (D-0073 `capture_case`, double-captured, byte-identical
  post-disposition): `mining_{use_ration_restore_write,
  use_ration_full_refusal,cook_campfire_write,use_torch_flavour}` —
  restore is the FIRST `mining_player_state` row-bearing golden
  (exemption retired, ratchet 9→10). Count pins → 491 / minted 29
  (reconciled with #387's fishing mints in-merge).
- Manifest: snapshot regen (4 workflow refs, no new command rows,
  post-#386 no-stable_hash format); PENDING-roster comments trued up.
- Verify @ a08ff1d: pytest 2516 passed / 2 skipped; gate GREEN 491/491;
  all 12 local check mirrors + manifest verify OK. ORDER 010 @codex
  comments posted on #385 and (retroactively) #384.

Decide-and-flag: (1) no fuzzy `resolve_item_name` — exact lowercase
names, the sell/buy/equip port posture; (2) cook keeps the oracle's
LEADING-digit amount parse, not the sell/buy trailing-qty grammar;
(3) in-txn re-checks refuse raced writes the oracle would dupe.

## 💡 Session idea

The kernel's ValidatorError envelope ("Missing/invalid argument: `…`.
`!help ?` for usage.") silently rewrites any oracle refusal raised
inside an op leg — invisible until a golden pins the byte, because no
imported sweep drives an in-leg refusal. Every future BLOCKED→LIVE flip
that carries verbatim refusal copy must compute its guards as
route-level pure reads (the sellall/quickcraft shape); worth one line in
`docs/parity/flip-playbook-traps.md` so slice 3's out-of-energy refusal
(and every later flip) doesn't re-derive it from a red capture.

## ⟲ Previous-session review

Previous card (`2026-07-13-energy-slice-1.md`, PR #384): the handoff
notes it left in the coordinator scratchpad (oracle clone path + pinned
sha, verbatim slice specs, store signatures, the unshallow gotcha) made
this session's boot near-zero-cost — the strongest cross-slice baton
this lane has produced; its base-branch evidence chain (enabler refuses
zero-required-contexts bases, proven by plain-push history rather than
a walled API read) is a model probe-before-wall.

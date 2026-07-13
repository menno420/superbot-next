# 2026-07-13 — mining energy slice 2: wire !cook/!use + argful goldens

> **Status:** `in-progress`

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

[[to be filled at flip]]

## 💡 Session idea

[[to be filled at flip]]

## ⟲ Previous-session review

Previous card (`2026-07-13-energy-slice-1.md`, PR #384): the handoff
notes it left in the coordinator scratchpad (oracle clone path + pinned
sha, verbatim slice specs, store signatures, the unshallow gotcha) made
this session's boot near-zero-cost — the strongest cross-slice baton
this lane has produced; its base-branch evidence chain (enabler refuses
zero-required-contexts bases, proven by plain-push history rather than
a walled API read) is a model probe-before-wall.

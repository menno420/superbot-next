# 2026-07-16 — conform sweep #457: raw→stripped D-0073 re-mint of every non-kernel golden

> **Status:** `in-progress`

- **📊 Model:** Fable 5 · default effort · parity-corpus conform sweep

## Scope

The #457 conform sweep, gate satisfied by the WP-lane merge (#497 landed
the stack): re-mint every raw-posture NON-KERNEL golden to the canonical
stripped D-0073 flavor — the #420/#449 precedent, now applied
corpus-wide. "Raw posture" = a golden whose bytes still carry the kernel
spine that `mint_golden`'s `apply_dispositions` strips from every
non-kernel golden: `audit_log` + `event_outbox` tables in `db_delta`,
and `command.dispatched` step events. Replay never diffs those bytes
(dispositions apply symmetrically to both docs in
`sb/adapters/parity/runner.py` `replay_case`), so verdicts are
unchanged; this is flavor normalization, not behavior change.

**Definitive target list — derived by structural marker scan at HEAD
(a047357), not inherited:** 35 of 523 goldens carry the markers; 4 are
`parity/goldens/kernel/*` and are EXEMPT per D-0075 (the kernel coverage
home keeps the spine deliberately — the strip INVERTED). That leaves
**31 targets**:

- **mining (28):** ascend, build_forge_insufficient, build_forge_write,
  cook_campfire_write, craft_no_recipe, craft_write, descend, equip,
  fastmine_out_of_energy_refusal, loadout_apply, loadout_delete,
  loadout_save, quick_craft, repair, reseed_world, respec_insufficient,
  respec_write, skill_bad_branch, skill_write, stash, stash_all,
  unequip, unstash, use_ration_full_refusal, use_ration_restore_write,
  use_torch_flavour, vault_upgrade (the `mining_*_write.json` WP/energy
  lane mints) + sweep_fastmine
- **cleanup (1):** cleanup_anti_evasion_toggle_write
- **creature (2):** creature_cbattle_bot_guard, creature_challenge_picker

Expected diff per golden: **pure deletions** of the disposition targets,
everything else byte-identical. Any golden whose re-mint diff shows
added/changed lines beyond the strip is drift — set aside
(`git checkout --`), reported, not committed, not chased in this PR.

## Floor + pin plan

`check_parity_depth`'s R3 ratchet counts golden bytes raw, so stripping
drops counted spine surfaces below the committed floors. Same-PR
narrated floor correction, the #449 precedent (fishing 3/10 → 2/8):
`parity/parity.yml` `depth.ratchet` mining {events: 4, tables: 17}
corrects downward by exactly the spine surfaces (audit_log/event_outbox
tables, command.dispatched event), which stay pinned in the `kernel`
coverage home; cleanup {2, 6} and creature {3, 6} are re-checked the
same way and corrected iff their counted surface also carried the
spine. Count pins re-summed FROM DISK via `tools/mint_golden.py`
`compute_counts` (the #497 merge-queue recipe), never hand-computed.
Corpus stays 523 — no golden added or retired.

Mint doctrine honored: local Postgres per the docs/CAPABILITIES.md
recipe (`tools/setup_local_env.py`), and the post-2026-07-13
CAPTURE_WORLD_WEATHER rule — weather-reading cases must have their
capture-day condition seeded in `sb/adapters/parity/runner.py`
`CAPTURE_WORLD_WEATHER` BEFORE any mint (#448/#449 lineage); the pure-
deletion diff check catches any date-derived byte that would drift.

## Verification

(filled at close-out — pytest full suite, check_parity_depth 49/49 +
523 goldens + ratchet OK, per-golden pure-deletion diff audit)

## 💡 Session idea

(filled at close-out)

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-16-merge-queue-landed.md` (#497). Its
count-pin recipe (union, then re-sum from disk via `compute_counts`
against the `GOLDENS_ROOT.glob("*/*.json")` corpus) is adopted verbatim
here for the pin re-sum. One observation this sweep makes concrete: the
WP/energy goldens that session landed were all minted BEFORE the D-0073
strip became the enforced canonical flavor, and nothing in the landing
path flagged them — a mint-time "raw markers present in a non-kernel
golden" preflight in `tools/mint_golden.py` would have made this whole
sweep unnecessary. See this card's close-out idea.

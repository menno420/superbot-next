# superbot-next · parity-flips wave-5 lane — durable lessons (2026-07-11)

> **Status:** `historical` — point-in-time retro, written at the lane's
> OWNER WRAP-UP DIRECTIVE (archive-prep) close-out. Session record:
> `.sessions/2026-07-11-parity-flips-wave5.md` (7 PRs:
> #197/#200/#201/#202/#203/#207/#211). Claims tied to PRs/commits;
> nothing here is carried from memory without a committed citation.

These are the lane's transferable lessons — patterns a successor session
(or the gen-2 blueprint) should start from rather than re-derive.

## 1. Trap-30 closure mechanics: compare VALUES, not just keys

`check_sim_gate` only redded NEW keys; a stale
`manifest/layout/*.lock.json` overlay silently masked a reshaped
manifest value because the overlay merged LAST on the "current" side
(#190's 3/2/2→3/3/1 reshape passed clean). The fix shape (#197,
`2d65739`) generalizes to any baseline-vs-derived checker:

- expose the DERIVED side before the overlay merge
  (`manifest_assignments()`), and red any key present on both sides
  whose values differ (`overlay_mask_problems()`);
- make the writer REFUSE on drift — `--write-baseline` exits 1 instead
  of re-pinning the stale value, so the amend is always a deliberate
  hand edit in the same PR as the reshape;
- expect a backlog: the first hardened run over HEAD found 42 standing
  masked drifts (6 real reshape residues + 36 seed-time `value: 0`
  placeholders). A checker-hardening slice should budget for amending
  what it unmasks, not just for the checker.

## 2. The #193 flip-sized law held — every re-home family needed real port work

Five families + one birth, 25 goldens, ZERO free greens. What each
family's reds forced (all port-side, never golden-side):

- ticket-admin (#200): two NEW stores + migration 0032, two K7 ops,
  two new panels, and a kernel selector seam (below);
- word→cleanup (#202): the shipped `_word_cache` process-memory port +
  oracle copy, and a retired exemption;
- xp-admin (#203): xpconfig panel + xpimport scan flow + resetxp
  one-shot, one exemption retired and one re-pathed;
- mod/channel strays (#207): a new ChannelLifecycleService + the
  shipped `channel.lifecycle_changed` advisory event + the modlogs
  card;
- starboard (#211): a full subsystem birth (migration 0033 + the whole
  trap-15 kit).

Successor rule of thumb: price an `_unmapped` re-home family as a
small FLIP (stores/panels/twins/seams), never as a file move. The law
has now held across role/counting (#193) and all six wave-5 slices.

## 3. RoleSelect type-6 seam (#200)

An options-source-less `SelectorKind.ROLE` renders as Discord's NATIVE
RoleSelect (wire component type 6) in BOTH presenters; provider-fed
ROLE selectors keep the string-select type-3 lane. The gate is the
EMPTY `options_source` — do not key it off the selector kind alone, or
provider-fed role pickers regress. (sb kernel panels + the parity
twin; goldens/ticket pins both wire shapes.)

## 4. verified_live.yml is an undocumented birth-kit step (#211)

The trap-15g "brand-new subsystem birth kit" list (domain package +
manifest module + lock seed + baseline + compat + manifest_compile)
is INCOMPLETE: the V4 verified-live gate also requires a
`verification/verified_live.yml` roster row for every subsystem key
(`starboard: unverified` landed with the birth). A birth PR that skips
it reds a named gate the kit list never mentions. Add the roster row
in the same commit as the parity.yml subsystem row.

## 5. check_symbol_shadowing vs store/service read pairs

A domain service re-exporting a store read under the same public name
reds `check_symbol_shadowing`. The ticket-style convention holds:
store-level reads take the `_row` suffix (`get_config_row`,
`get_settings_row` — sb/domain/ticket/store.py,
sb/domain/starboard/store.py) while the service keeps the domain name
(`get_config`, `get_settings`). Rename at the store, never suppress
the checker.

## 6. Worker-stall / resume cadence

The band-7 observation (ops-notes item 4) reproduced in this lane:
long port-slice workers stall roughly twice per slice — after pushing
(“waiting for CI”) and after the local ladder. Treat a stopped worker
as PAUSED, not done: re-message with the remaining ladder
(forward-merge check → CI verify at the head → merge → post-merge
count fold) and it resumes cleanly. Budget coordinator pokes into
every slice's timeline; none of the seven PRs needed rework because of
a stall, only wall-clock.

## 7. Small confirmations worth keeping

- `--write-ratchet` is comment-preserving post-#199 — verified in
  anger across four re-home PRs; the run-learn-restore hand-apply
  workaround is dead.
- The #207 strays were NOT the create-channel wall (the quicksetup
  channel-ops decision record in docs/decisions.md): their goldens pin
  fake_http EDIT verbs (slowmode/lock/unlock). Check which wire VERB a
  stray family pins before assuming the wall — it walls creation, not
  mutation.
- Compensator allowlist stayed EMPTY through a wave that added K7
  write ops in three PRs
  (tests/unit/workflow/test_compensator_invariant.py `_ALLOWLIST` is
  `{}` at HEAD) — new audited ops keep landing without allowlist
  growth; treat any proposed entry as a defect ledger, not a
  convenience.

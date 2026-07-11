# 2026-07-11 — parity flips wave 5 (trap-30 hardening + the `_unmapped` re-home wave + the starboard birth)

> **Status:** `complete`

- **📊 Model:** Fable · high · bug fix (Q-0194)

## Scope

The wave opened as the trap-30 hygiene fix (the #190 role-flip ledger
follow-up — the sim-gate value-drift checker) and grew into the
parity-flips lane's full `_unmapped` re-home wave under Q-0265
continuous mode: five re-home families onto ported rows plus the
starboard subsystem BIRTH. Seven PRs merged green this wave, each its
own squash-merged-on-green PR on the 6-check ruleset (`report`
red-by-design, non-required). The session ended on the OWNER WRAP-UP
DIRECTIVE (archive-prep): enders only — this card's completion flip,
the retro lessons doc and the final status fold ride the wrap-up PR.
The Model line above stays as first committed at #197 (the card + its
telemetry row shipped there; one row per card, not re-added at the
flip — the #209 precedent).

## The seven PRs (each merge sha verified against `git log origin/main` at `323e304`)

1. **#197** `2d65739` — trap-30 checker hardening: `check_sim_gate`
   reds overlay-masks-manifest VALUE drift, `--write-baseline` refuses
   on drift; 42 pre-existing masked drifts amended to manifest truth
   (6 real reshape residues + 36 seed-time `value: 0` placeholders).
   Full mechanics in the section below (the card's original scope).
2. **#200** `870a16c` — ticket-admin family (6) re-homed
   `_unmapped`→ticket (ticket row 12/12): ticket_blacklist +
   ticket_config stores (migration 0032), K7 ops, launcher/setup
   panels, and the NEW kernel seam — options-source-less
   `SelectorKind.ROLE` renders as the native RoleSelect (wire type 6)
   in BOTH presenters.
3. **#201** `99962a6` — lane heartbeat (the #197/#200 fold; gate
   245/245 CI-log-verified, `_unmapped` 201→195).
4. **#202** `2f4b2c3` — word family (4) re-homed `_unmapped`→cleanup
   (cleanup row 7/7): oracle copy + the shipped `_word_cache` ported;
   the `table:prohibited_words` covered-elsewhere exemption RETIRED
   (the family's own goldens carry the row now).
5. **#203** `ab1e916` — xp-admin family (4) re-homed `_unmapped`→xp
   (xp row 7/7): xpconfig panel + xpimport scan flow + resetxp
   one-shot; the `event:xp.reset` covered-elsewhere exemption RETIRED
   (sweep_resetxp carries the event verbatim), `event:xp.level_up`
   re-pathed onto surviving citations.
6. **#207** `2c62a09` — moderation/channel strays (5) re-homed
   `_unmapped`→moderation+channel (moderation 10/10, channel 4/4):
   modlogs card + the ChannelLifecycleService slice with the shipped
   `channel.lifecycle_changed` advisory event
   (sb/domain/channel/service.py). NOT the D-0030 create-channel wall
   — these goldens pin fake_http EDIT verbs (slowmode/lock/unlock),
   not channel creation.
7. **#211** `a283f3f` — starboard subsystem BORN ported (6 goldens
   re-homed onto the NEW row — 38/50): the shipped `!starboard` config
   group + config panel at byte parity, migration 0033, the full
   birth kit (trap 15b/g) PLUS the undocumented birth-kit step — a
   `verification/verified_live.yml` roster row (`starboard:
   unverified`), required by the V4 gate. ONE new depth exemption row
   (`table:starboard_settings`) under the EXISTING
   `guard-only-capture` class (D-0069) — zero new reason classes.

## End counts (wave-5 END state, CI-log-verified at main `a283f3f`, #211's merge)

- gate **GREEN 264/264 across 38 ported** — golden-parity run
  29166086847 gate job 86579320344: "gate: GREEN — all 264 golden(s)
  across 38 ported subsystem(s) replay clean" + "golden-parity gate:
  38 ported / 12 pending" + "check_parity_depth: OK — 50 subsystems
  (38 ported), 467 goldens" (same job).
- report **301/467 green, 467/467 replayable, 38/50 ported** — report
  job 86579320337 same run: "green: 301/467 replayed cases match their
  golden" + "replayable: 467/467" + "ported: 38/50 subsystems";
  per-subsystem table: starboard 6/6, ticket 12/12, moderation 10/10,
  channel 4/4, cleanup 7/7, xp 7/7 [all ported], `_unmapped` 35/176
  [pending].
- units **1456 passed / 4 skipped in CI** (ci run 29166086818 tests
  job 86579320209; the local canonical ladder differs by the standing
  guarded-import skip delta).
- corpus **467 = 465 imported + 2 minted**; `_unmapped` **201 → 176**
  across the wave (25 goldens re-homed: 6+4+4+5+6).
- compensator allowlist EMPTY throughout
  (tests/unit/workflow/test_compensator_invariant.py `_ALLOWLIST = {}`);
  zero new exemption/disposition CLASSES all wave (one new ROW under
  the existing guard-only-capture class, two rows retired — net −1).

## The original #197 scope (trap-30 mechanics, unchanged record)

Trap-30 hygiene fix (the #190 role-flip ledger follow-up,
control/status.md #190 entry: "a value-comparing checker is the hygiene
follow-up"): `tools/check_sim_gate.py` did not flag VALUE drift on an
existing [A] pin — `current_assignments()` merged the
`manifest/layout/*.lock.json` overlays LAST, so a stale overlay value
overwrote the manifest-derived value before the diff; both "current" and
the baseline carried the OLD value while the manifest shipped the NEW
one, and nothing redded (observed on #190: role.hub's 3/2/2→3/3/1
reshape passed silently).

What shipped in #197:

1. **The value-comparing checker** (`tools/check_sim_gate.py`):
   `manifest_assignments()` exposes the raw manifest-derived [A]
   assignments BEFORE the overlay merge, and `overlay_mask_problems()`
   reds any key present on BOTH sides whose overlay value differs from
   the manifest-derived value (overlay-masks-manifest drift), naming the
   key, the overlay value, and the manifest value. `check()` runs it;
   `--write-baseline` REFUSES (exit 1) instead of silently re-pinning a
   stale overlay value. Overlay-ONLY keys (legacy-seed Exempt rows with
   no manifest-derived counterpart — the setup `WizardSectionSpec.order`
   seeds) stay legitimate; auto-exempt below-floor keys stay outside the
   gate's jurisdiction, matching every other check.
2. **42 existing masked drifts found and amended to the manifest truth**
   (the first run of the hardened checker over HEAD redded them all):
   - 6 REAL reshape residues, exactly the #190 class:
     `games:games.world` ×3 (manifest gained `world_deathmatch` +
     `world_casino`; lock/baseline still pinned the 2-row split without
     them) and `server_management:server_management.hub` ×3 (the #179
     `help_back` row never reached the lock/baseline).
   - 36 seed-time `"value": 0` placeholders (ai ×24 — 4 panel layout
     trios + 11 `SettingSpec.group` + 1 `BindingSpec.group`; btd6/chain/
     counting/projmoon hub trios ×3 each) that had masked every reshape
     of those keys since the legacy seed.
   Provenance untouched (all legacy-seed Exempt); baseline regenerated
   via the hardened `--write-baseline` — 738 pins, zero keys
   added/removed, exactly 42 values changed, zero provenance churn.
3. **Regression tests** (`tests/unit/sim_runner/test_run_and_gate.py`,
   `TestOverlayMasksManifestDrift`): overlay masking a reshaped manifest
   value → red; overlay-only key → still green (check + write-baseline);
   `--write-baseline` refusal on drift (baseline file byte-unchanged);
   matching overlay value → green. 45/45 sim_runner tests pass.

## Traps confirmed / new intel

- **Trap 30 closed at the checker**: the masked-drift class can no
  longer pass silently; a reshape now demands the lock amendment in the
  same PR (the #190 hand-amend recipe is now machine-enforced).
- **The seed placeholders were a standing mask**: `"value": 0` entries
  (band-6/7 seeds) made every subsequent reshape of those keys
  invisible to the gate — the games.world deathmatch/casino row and the
  server_management help_back row both slipped through this hole.
- **The #193 flip-sized law HELD across all five re-home families +
  the birth**: every family's reds were real port gaps fixed PORT-side
  (new stores/panels/twins/seams per family; 25 goldens, zero free
  greens). Budget re-homes as flips, never as file moves.
- **The birth kit has an undocumented step**: a NEW subsystem row also
  needs its `verification/verified_live.yml` roster row (`<key>:
  unverified`) or the V4 verified-live gate reds — not in the trap-15g
  birth-kit list (#211; the retro lessons doc carries the recipe).
- **`--write-ratchet` is comment-preserving post-#199** — verified in
  anger this wave; the run-learn-restore hand-apply dance is retired.
- **`check_symbol_shadowing` reds duplicate public read names** across
  store/service modules — use ticket-style `get_<thing>_row` renames
  (#200/#211 bites).
- Trap 25 honored: no Postgres ladder run in the wrap-up seat; wave
  counts are CI-log-verified at each PR head / main push instead.

## Verification

Every merge sha verified against `git log origin/main` at `323e304`;
end counts CI-LOG-VERIFIED at main `a283f3f` (the End-counts section
above carries run/job ids per claim); `python3 bootstrap.py check
--strict` green at the wrap-up head; no open PRs and no unmerged
`wave5/*` branches remain (the seven `origin/wave5/*` refs are the
merged PRs' squashed source branches; control/claims/ holds no wave-5
claim files).

## 💡 Session idea

The remaining `_unmapped` 176 is now MAPPED territory, not a fog: 62
are btd6-family sweeps over the PORTED btd6 row (30 `slash_btd6_*` +
btd6events/btd6ops/btd6ref/btd6strat — a band-7-successor re-home
wave), 36 are fishing/mining game sweeps over PENDING rows (band-6
lane; blocked on those rows porting first), 3 are setup strays (PARKED
with trap 17), and ~75 are mixed singletons (fun/general cards,
channel-ops-adjacent admin strays, game-economy singles). The
btd6-family re-home is the highest-leverage next slice: one family,
one ported target row, the #193 law already priced in.

## ⟲ Previous-session review

(Covers the #193 re-home lane, `.sessions/2026-07-11-role-counting-rehome.md`,
this lane's direct predecessor.) Its law — "re-homes over a ported row
are FLIP-SIZED, not free" — held on every family this wave: ticket
needed two new stores + a kernel selector seam, word needed the
`_word_cache` port, xp-admin needed three new surfaces, mod/channel
needed a new domain service + event, starboard needed a whole birth
kit. Its remaining-map probe list (ticket-admin, word, xp-admin,
mod/channel strays, starboard-needs-a-row-first) was exactly the wave
that shipped, in order — zero surprises in the map, and its corrected
starboard count (6, not 7) was right. What it under-called: it framed
starboard as "needs a subsystem row first" without naming the
verified_live.yml roster row that the birth actually tripped on; and
its #190-derived hygiene prescription (the value-comparing checker)
was scoped as a checker fix but surfaced 42 standing masked drifts —
an order of magnitude more amendment than the prescription implied.
Its verification discipline (CI-log counts at the PR head, shas from
origin/main) transferred verbatim and is what this card mimics.

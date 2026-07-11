# 2026-07-11 — band-7 builder session (Knowledge + AI, continuous mode Q-0265)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Band 7 = Knowledge + AI, deterministic-first per the rebuild completion
report §5 step 9. The lane opened on the band-6 wrap-up's Q-0265
honesty-guard ruling (no golden-pinned game work left → canonical order
says band 7) and ran continuously — slice after slice, each its own
merged-on-green PR on the 6-check ruleset. Twelve PRs merged this
session; every sha below verified against origin/main at `f986177`.

## The twelve PRs (one line each)

1. **#141** `78509df` — test-order flake killed: `register_ops()` in
   rps + blackjack now ends with the idempotent `ensure_ops_refs()`
   (the sanctioned `clear_ref_table` seam left cached ops modules'
   workflow leg refs unregistered under non-canonical pytest orders).
2. **#144** `596fb2d` — btd6 pending→ported at byte parity, 39/39
   goldens (the shipped unified `!btd6` tree); NEW `modal-driven`
   depth reason class minted (record D-0063 rode #147).
3. **#147** `9f83ea1` — lane heartbeat 1 (#141/#144 records) +
   D-0063.
4. **#148** `f2dcf0d` — project_moon + projectmoon pending→ported in
   one slice, 11/11 goldens (the shipped `!pm` LimbusBrowseView +
   `/pm` ephemeral slash twin).
5. **#151** `1bea65d` — ai pending→ported, the band's largest row:
   20/20 goldens fixed-in-PR (deterministic operator surface; two
   replay-harness semantics changes flagged corpus-wide); the live-NL
   leg stays owner-key-gated.
6. **#153** `119ecce` — lane heartbeat 2 (#148/#151 records) +
   OWNER-ACTION 5 (the AI key envelope) graduated to needs-owner.
7. **#155** `4c8c5b0` — the `!aireview` review-loop + presets surface;
   11 sweep_aireview goldens re-homed `_unmapped`→ai (ai 31 total);
   the `ai_answer_presets` depth exemption REMOVED.
8. **#156** `179dfb2` — k10 test-order flake fix, test-only: the
   orchestration suite isolates the AI registries in both directions.
9. **#160** `0a29d37` — ai policy/behavior/tools chooser PAGES + the
   S6/S7 settings edit/reset widgets over the audited
   `settings.set_scalar` lane (one real codex P2 fixed in-PR).
10. **#162** `dd626b2` — lane heartbeat 3 (#155/#156/#160 records) +
    ORDER 012 done.
11. **#165** `62d850f` — the live MODAL-SUBMIT lane arms (D-0054's
    wire-type-5 successor, record D-0066); the #160-parked ai
    free-text/Override editors ship on it; codex P2 taken in-PR
    (modal-args stash re-keyed per originating message).
12. **#177** `f986177` — the ai policy SCOPE PICKERS go live (record
    D-0070): migration 0028 typed override tables, one audited
    `ai.set_*_policy` op per scoped write, the K10 overlay reader,
    native type-8 channel select; codex triage 2 taken / 1 declined.

## Band-7 position at wrap-up

All three golden-pinned deterministic rows are PORTED (btd6 39, ai 31
incl. the aireview re-home, project_moon 10 + projectmoon 1). Counts
re-measured at `f986177` (main HEAD) from main-push CI: gate GREEN
**175/175 across 32 ported** (golden-parity run 29152481842, gate job
86544105424; check_parity_depth OK — 49 subsystems, 465 goldens);
report **212/465** green, 465/465 replayable, all four band-7 rows
green-ported in the per-subsystem table (report job 86544105417);
units **1372 passed / 4 skipped** in CI (run 29152481834 job
86544105246), 1374/2 local canonical with deps; `_KNOWN_ENSURE_ONLY`
hand-count **45** = mining 28 / fishing 15 / creature 1 / role 1 —
zero band-7 refs remain (was 99 when #114 minted the ledger; #144
burned 23, #148 burned 10, #151 burned 20, and the parity lane's #145
pruned proof_channel's 1).

## Parked map (the honest remainder)

- Behavior-preset slice + orchestration-mutation slice — parked per
  D-0070 (need the preset catalog / ai_instruction_profile /
  apply_preset seam, resp. ai_orchestration_mutation + the
  orchestration_profile columns).
- Replay modal vocabulary + btd6 strategy form goldens — the D-0066
  successors (the depth exemptions' deletion path: a `modal` step kind
  in case reconstruction + type-5-carrying goldens + the strategy
  form).
- Review-channel poster — parks with NL arming.
- Live-NL leg (NL shell, verify_and_regenerate_once, live routing) —
  owner-key-gated, OWNER-ACTION 5 stands (`ANTHROPIC_API_KEY` +
  `AI_ENABLED` absent from the session env, verified at #151's live
  drive).
- Testing-report row 9 (band 7) stays pending until the band's own
  live-testing pass (the band-6 row-8 convention).
- #144 domain parked items (freeplay MOAB scaling, maps/modes
  resolver, boss estimator, CT guided-set, ops seed-data) and #148
  items (edit-in-place vs result cards, audience split) unchanged.

## Honest notes

- **Codex flap + one phantom, documented**: the connector answered the
  lane's mid-session questions with usage-limit replies (#148 comment
  4942100526, #151 comment 4942514698), then returned REAL reviews
  the same morning — but the #160 reply (comment 4943407864) claimed
  a commit `64d607a` + follow-up PR that exist nowhere (documented on
  the PR at comment 4943535922; the Q-0120 verify-before-acting guard
  held, no action taken on invented artifacts). #144's earlier reply
  had likewise claimed an invisible regression-test PR. The real
  findings that survived verification were fixed (#160 P2 in-PR, #165
  stash-key P2, #177 triage 2-taken/1-declined with citations).
- **Two mid-session worker stalls, resumed**: two slice workers
  stalled mid-task during the session and were resumed by the
  coordinator; both slices landed normally (no lost work, no
  duplicate PRs).
- **Record errors corrected in-ledger**: the #144/#148 PR bodies
  carried a +23 offset in the ensure-only burn-down counts — the file
  counts are the measured truth (lane record in control/status.md).
- **Commit-body typo, ledgered**: #177's first commit message says
  "D-0067 ledgers the engine-shape deviations"; the committed decision
  record is D-0070 (docs/decisions.md).

## Verification

Every count above read from CI logs or the repo at `f986177`, not
carried forward: gate/report/depth from golden-parity run 29152481842,
units from ci run 29152481834, parity.yml 32 ported / 17 pending and
`_KNOWN_ENSURE_ONLY` 45 counted by hand at the same sha; all twelve
merge shas verified against `git log origin/main`.

## 💡 Session idea

The next band-7 wake has a clean fork: (a) the behavior-preset slice
is the natural continuation (it unblocks the parked preset pickers AND
the `instruction_profile_id` FK target), or (b) if the owner lands
OWNER-ACTION 5 first, the live-NL leg jumps the queue since it is the
band's done-when. Either way, the D-0066 replay-modal-vocabulary
successor is the highest-leverage shared infrastructure: it deletes
depth exemptions across TWO reason classes (modal-driven +
select-driven) in one corpus-schema change.

## ⟲ Previous-session review

(Covers the band-6 games session, `.sessions/2026-07-11-band6-games-session.md`.)
Its wrap-up ruling ("no golden-pinned game work left → next wake
starts band-7 per the canonical order") is exactly what this session
executed. Its composition-parity invariant (#114) paid for itself
twice here: the ensure-only burn-down ledger structured three of this
lane's flips (btd6/projmoon/ai each registering at import), and its
`_KNOWN_ENSURE_ONLY` list is now the band-boundary map (45 refs, all
in unported bands). Its parked note on test-order flakes was closed by
this lane's #141 and #156 — the doctrine (register at import; suites
isolate registries both directions) held for every subsequent slice.

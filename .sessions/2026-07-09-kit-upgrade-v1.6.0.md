# 2026-07-09 — vendored kit upgrade to substrate-kit v1.6.0

> **Status:** `complete`

## Scope

Third real-world run of the kit's `upgrade` verb (v1.0.0 → PR #46, v1.2.0 →
the prior upgrade session): move the vendored `bootstrap.py` from v1.2.0 to
the released v1.6.0 (sha256
`787d561728f64070efd7e25db05a1264db24b4bee66b08a296ebd205d6d8060f`, verified
against `release.json`, `bootstrap.py.sha256`, and the release-asset digests
before starting). Deltas inherited since 1.2.0: v1.3.0 heartbeat `kit:` line +
adopters registry, v1.4.0 configurable `heartbeat_files`, v1.5.0
CAPABILITIES.md + orientation wiring + close nudge, v1.6.0 owner-action
six-field checker + order-claim convention.

- **📊 Model:** claude-fable-5 · high · mechanical upgrade + doc reconcile

## What shipped

- **Upgrade per §4.3:** sha256 verified three ways before starting (release
  API digest, `.sha256` asset, `release.json`), then by the verb itself;
  state.json banked; old-dist archive idempotent-silent
  (`bootstrap-1.2.0.py` was already banked by the previous upgrade's adopt
  pass — the known cosmetic output quirk, still present, see findings); new
  dist banked for the next upgrade (`bootstrap-1.6.0.py`); vendored
  `bootstrap.py` replaced v1.2.0 → v1.6.0; `kit_version: 1.6.0` in config +
  state; `heartbeat_files: ["control/status.md"]` (the v1.4.0 default)
  written to config; inputs self-cleaned (`bootstrap.py.new` +
  `release.json` removed by the verb — nothing strayed into the PR);
  `last-upgrade.json` honest: `from_version: "1.2.0"`,
  `archived_dist: bootstrap-1.2.0.py`.
- **Upgrade-report classification (run 1, canonical):** consumer-edited 7 ·
  diverged 2 (`control/README.md`, `control/status.md`) · missing 1
  (`docs/CAPABILITIES.md`) · template-improved 3 · unchanged 6.
- **`--apply-docs` on the 3 safe rows** (via the kit's own
  `--rollback` → re-run lane, since the first run had already consumed the
  apply window): CONSTITUTION.md gains the capabilities-discovery +
  owner-attention rails; docs/collaboration-model.md gains "Routing work to
  the owner"; docs/AGENT_ORIENTATION.md wires CAPABILITIES.md into the
  reading order. All three hash re-recorded; zero unrendered slots after.
- **CAPABILITIES.md planted** fully rendered (0 UNRENDERED banners, 0
  `${...}` slots — this install's interview is complete, so the adopt pass
  rendered it live). The rollback/rerun dance lost run 1's hash record for
  it (run 2 classified it "diverged — no recorded hash"); fixed kit-natively
  by deleting + idempotent `adopt` replant — byte-identical
  (`d367b798…6aa6f6`) and hash now recorded, so future upgrades classify it
  honestly.
- **Diverged control docs manually merged** (the report's manual lane):
  `control/README.md` gains the v1.3–v1.6 protocol extensions — per-lane
  heartbeats, order-claiming (claim FIRST on your own status line, landed on
  main; ~24h expiry), the `kit:` status line, the OWNER-ACTION six-field
  format. `control/status.md` overwritten as this session's heartbeat: new
  `kit: v1.6.0 · check: green · engaged: yes` line, ⚑ needs-owner rewritten
  into three six-field OWNER-ACTION items with honest VERIFIED-NEEDED values
  (flag-13 ruling = product-policy decision; plugin-hello repo = captured
  403 on token repo-create; merge-dance = admin-only ruleset, #86/#87
  evidence), band-5 state carried unchanged.
- **New owner-action advisory verified live:** before the rewrite,
  `check --strict` fired `[owner-action-fields]` on `control/status.md`
  (non-`none` ⚑ needs-owner, six labels absent) — advisory-only as released,
  exit unaffected; after the rewrite it is silent. Guard-fire telemetry row
  recorded in `.substrate/guard-fires.jsonl` (committed).
- **Verified after:** `bootstrap.py --version` → 1.6.0; `adopt` gate:
  ENGAGED green; `check --strict` red ONLY on this card's own born-red badge
  before close-out (the gate as designed); pytest 1124 passed / 1 skipped;
  `manifest_compile` + all 21 committed checkers green locally
  (golden-parity's DB leg left to CI's Postgres, as always).
- **NOT installed, deliberately (same decision as the v1.2.0 upgrade):** the
  staged `.substrate/ci/substrate-gate.yml` — ci.yml already runs
  `check --strict` and the owner's 6-check ruleset stands.

## Kit findings (reported upstream, not worked around)

- **The `--apply-docs` window is single-shot and the note undersells it:**
  the verb prints "re-run with --apply-docs to take them" — but a literal
  re-run cannot work: the inputs were just self-cleaned AND the vendored
  dist is already the new version, so the old templates the diff needs are
  gone (old==new → the 3 rows reclassify as unchanged/diverged). The actual
  recovery lane is `upgrade --rollback` + re-download/re-run with
  `--apply-docs`, which works but has a side effect (next finding).
  Suggestion: either make the note say that, or support a post-hoc
  `upgrade --apply-docs` that diffs against the archived old dist (it is
  always banked by step 2).
- **Rollback+rerun loses adopt-pass hash records:** run 1's adopt pass
  planted CAPABILITIES.md and recorded its hash; `--rollback` restored the
  pre-upgrade state.json (correct), but run 2 then classified the
  still-on-disk CAPABILITIES.md as "diverged — no recorded hash" and kept it
  WITHOUT re-recording — a permanent manual-review row for a byte-identical
  kit-planted file. Worked around kit-natively (delete + idempotent `adopt`
  replant re-recorded it). Suggestion: when a kept doc byte-matches the NEW
  template render, record its hash instead of leaving it unclassifiable.
- **Cosmetic, carried from the v1.2.0 report and still present:** on the
  idempotent old-dist-archive path the only `archived:` line printed names
  the NEW dist (the adopt pass banking for the next upgrade); a skimmer can
  read it as the old-dist archive. Same suggestion as before: print
  `archived: … (already banked)` or label the adopt line
  `banked for next upgrade:`.
- **Owner-action checker behaved exactly as released** — advisory-only, one
  finding per heartbeat file, correct six-label detection, silent once the
  labels exist, telemetry recorded. No bug.

## 💡 Session idea

The `kit:` status line (`check: green|red`) is written by hand and instantly
stales — this session had to caveat "green = post-card-flip verdict" in
notes because the honest live verdict flips within the same session. A
cheap kit follow-up: `bootstrap check --stamp-status` (or a flag on the
existing status checker) that rewrites the `kit:` line's `check:` +
`engaged:` fields from the verdict it just computed, so the
substrate-coordinator channel is generated evidence rather than a claim —
the same "verifiable output" bar the rest of the fleet applies, and it
closes the one field an adopter can fake by typo.

## ⟲ Previous-session review

The v1.2.0 upgrade session (the previous kit-lane session on this repo) set
a strong template — its sha256-twice discipline, its "observe both #46
fixes in the field" framing, and its deliberate not-installing of
substrate-gate.yml all transferred verbatim and were simply re-executed
here. Two of its outputs paid off directly this session: its cosmetic
`archived:`-line finding gave this session a known-issue to re-verify
(still unfixed — re-reported), and its close-out flag about arming
auto-merge only after the card flip is what kept this PR safe from the #44
class again. What it could have done better: it used `--apply-docs`'s
absence that run (nothing was safe to apply) and so never discovered that
the apply window is single-shot — a one-line "how would a session take
template improvements AFTER the run?" probe would have surfaced the
rollback side effect a release earlier. System improvement this surfaces:
upgrade-lane sessions should treat every kit verb they DIDN'T need as a
one-command smoke probe, because the next session will need it.

## ⚑ Flags

- Self-initiated: manually merged the v1.3–v1.6 control-protocol template
  deltas into `control/README.md` (the report's manual lane, additive-only,
  reversible by git) and rewrote the heartbeat's ⚑ needs-owner into the
  six-field format with real VERIFIED-NEEDED values.
- Self-initiated: used `upgrade --rollback` + re-run to reach
  `--apply-docs` (kit-native, archive-backed), then delete+`adopt` to
  restore the lost CAPABILITIES.md hash record — both reported upstream as
  kit findings rather than silently absorbed.
- Deviation from generic convention, deliberate (same as the v1.2.0
  session): auto-merge armed as the LAST step after this card flipped
  complete — this repo's `check --strict` runs in the non-required
  `checkers` job, so a born-red card cannot hold auto-merge here (#44
  lesson).
- Not done here, on purpose: the kit-side adopters-registry row
  (`docs/adopters.md` kit_version → 1.6.0 in menno420/substrate-kit) is
  kit-side work, handled separately.

# 2026-07-10 — vendored kit upgrade to substrate-kit v1.7.0

> **Status:** `complete`

## Scope

Fourth run of the kit's `upgrade` verb on this repo (v1.0.0 → v1.2.0 →
v1.6.0 → now v1.7.0): move the vendored `bootstrap.py` from v1.6.0 to the
released v1.7.0 (tag `93c7bdb`, release asset sha256
`00f4f4cd39351b17389b9abab3be88fcb0c9f4dee9ad8f1639ad1fc67fdb5238`).
Kit-owned files only — no domain work; `control/inbox.md` and
`control/status.md` untouched by directive (the lane's own next heartbeat
records the `kit:` line).

- **📊 Model:** claude-fable-5 · high · mechanical kit upgrade

## What shipped

- **Upgrade per §4.3:** release asset digest verified before running
  (matches the runbook pin byte-for-byte), then re-verified by the verb
  itself against the adjacent `release.json`. State banked
  (`.substrate/backup/state.json`, `last-upgrade.json` honest:
  `from_version: "1.6.0"`); new dist banked for the next upgrade
  (`bootstrap-1.7.0.py`); vendored `bootstrap.py` replaced v1.6.0 → v1.7.0;
  `kit_version: "1.7.0"` recorded in config; inputs self-cleaned by the verb
  (nothing strayed into the PR). `session_markers` already carried the
  `📊 Model:` needle from the pin session, so step 6b was a no-op.
- **Upgrade-report classification:** unchanged 10 · consumer-edited 8
  (all left alone, including both control seam files) · diverged 1
  (`control/README.md`). Ran with `--apply-docs`; zero template-improved
  rows existed, so nothing auto-rewrote — the v1.6.0 session's manual
  merges are why most template deltas were already in.
- **Diverged doc manually merged (the report's manual lane):**
  `control/README.md` takes the one additive template delta — the
  `bootstrap adopt --lane <name>` "one command, not hand-edits" bullet
  (v1.7.0 #103, the double-adoption fix). Additive-only, reversible.
- **Staged `.substrate/` artifacts regenerated;** the only byte change is
  the staged `ci/substrate-gate.yml` (+28/−4: the #95/#99 no-card sentinel
  + born-red ADDED-card template fixes). Still NOT installed as a live
  workflow — same deliberate decision as the v1.2.0/v1.6.0 sessions;
  ci.yml already runs `check --strict`.
- **Known and expected:** the PR #130 kit-ownership change (live
  substrate-gate.yml regenerated on every adopt/upgrade) is post-v1.7.0
  and does not apply on this upgrade — next release's wave.
- **Verified after:** `bootstrap.py --version` → 1.7.0; `check --strict`
  red only on this card's own born-red badge before close-out (the gate as
  designed) plus one advisory (below); pytest 1157 passed / 2 skipped;
  `manifest_compile` OK.

## Kit findings / flags for the lane

- **New v1.7.0 `[owner-ask-wall-unrecorded]` advisory fires live on
  `control/status.md`:** OWNER-ACTION 3 (branch-update merge dance) cites a
  technical wall that `docs/CAPABILITIES.md` does not record. Advisory-only,
  never exit-affecting — and acting on it means editing the heartbeat seam,
  which is out of this session's directed scope. **Left for the lane's next
  heartbeat session:** append the wall to CAPABILITIES.md per THE DISCOVERY
  RULE step 4, alongside the `kit: v1.7.0` line update this session also
  deliberately skipped.
- The v1.6.0 session's two upstream findings are FIXED in this release as
  advertised: the post-hoc `--apply-docs` mechanism exists (#106) and the
  upgrade ran clean in one pass — no rollback dance needed this time.

## 💡 Session idea

The upgrade report's `diverged` lane prints a template@old→new diff and
says "manual merge" — but when the delta is purely additive (this session's
`control/README.md` case: 4 added lines, zero removed/changed), the merge
is mechanical and every adopter session performs it by hand-copying from
the report. Cheap kit follow-up: classify additive-only diverged deltas as
`diverged-additive` and offer `upgrade --apply-additive` (or a per-file
prompt) that appends the hunk via a real 3-way merge, keeping true
conflicts manual. Three upgrade sessions on this repo have now done this
same copy-paste; the class is common enough to automate.

## ⟲ Previous-session review

The v1.6.0 upgrade session set the template this one executed almost
verbatim, and its two payoffs landed exactly as designed: its kit findings
(single-shot `--apply-docs` window, rollback hash-record loss) shipped as
v1.7.0 #106/#92, so this session needed zero workarounds — the
find-upstream-fix-next-release loop demonstrably closed; and its close-out
flag (arm auto-merge only after the card flip, since `checkers` is
non-required) again kept this PR safe from the #44 class. What it could
have done better: its manual merge of the control/README.md template deltas
left the doc in the permanent `diverged` class, which is what forced this
session's manual lane again — it could have flagged "this doc will diverge
on every future upgrade" as a standing cost, which is precisely what the 💡
above now proposes fixing kit-side. System improvement: an upgrade-lane
session should end by predicting which classification rows the NEXT upgrade
will see — a one-line forecast turns the report into a regression check.

## ⚑ Flags

- Self-initiated: manually merged the additive `adopt --lane` template
  delta into `control/README.md` (the report's manual lane; same precedent
  as the v1.6.0 session's control-doc merges; additive-only, reversible).
- Deviation, directed (Q-0261.3): `control/status.md` `kit:` line NOT
  updated this session — the checklist step is deliberately skipped; the
  lane's own next heartbeat records `kit: v1.7.0`.
- Deviation from generic convention, deliberate (same as v1.2.0/v1.6.0):
  auto-merge armed as the LAST step after this card flipped complete —
  this repo's `check --strict` runs in the non-required `checkers` job, so
  a born-red card cannot hold auto-merge here (#44 lesson).

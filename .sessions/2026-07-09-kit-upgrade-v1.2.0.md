# 2026-07-09 — vendored kit upgrade to substrate-kit v1.2.0 + engagement render

> **Status:** `complete`

## Scope

Second real-world run of the kit's `upgrade` verb (first was v1.0.0, PR #46):
move the vendored `bootstrap.py` from v1.0.0 to the released v1.2.0
(sha256 `258ab02aa54811d91b013f67a15d4bf13e8fc917421434746dd3ca26bc59098c`,
verified against `release.json`), then walk the new KL-7 engagement gate to
GREEN — this repo was fleet-flagged as stranded (9 planted docs still under
the adopt-time UNRENDERED banner with 8 unfilled `${...}` interview slots).

- **📊 Model:** claude-fable-5 · high · mechanical refactor

## What shipped

- **Upgrade per §4.3:** sha256 verified twice (locally against
  `bootstrap.py.sha256`, then by the verb itself against `release.json`);
  old dist archived (`.substrate/backup/bootstrap-1.0.0.py` — already banked
  by an earlier session, archive idempotent-identical) + state.json banked
  before any overwrite; vendored `bootstrap.py` replaced v1.0.0 → v1.2.0;
  staged `.substrate/` artifacts regenerated (incl. the new staged
  `.substrate/ci/substrate-gate.yml`); `kit_version: 1.2.0` recorded in
  state + config; 📊 Model needle appended to `session_markers` by the verb
  itself (the KL-3 tighten-at-upgrade behavior, seen live).
- **Both #46 kit fixes verified in the field:** (1) from-version honesty —
  report title reads "v1.0.0 → v1.2.0" and `last-upgrade.json` records
  `from_version: "1.0.0"` / `archived_dist: bootstrap-1.0.0.py` (the old
  config-pin echo would have been right by coincidence here; the code now
  prefers the vendored header, per the comment citing superbot-next#46);
  (2) input self-cleanup — the verb removed `bootstrap.py.new` and
  `release.json` after the replace ("cleaned up: … pass --keep-inputs to
  retain"), so nothing strays into this PR.
- **Upgrade-report classification:** 12 `consumer-edited` (template
  unchanged, nothing to apply) · 6 `diverged` · 0 `template-improved` →
  `--apply-docs` had nothing safe to apply and was correctly not used.
  Three diverged docs carried real template deltas (v1.1.0 additions);
  manually merged all three per the report's manual-merge lane:
  CONSTITUTION.md + docs/collaboration-model.md gain the **Program law**
  pointer section (cite PL-IDs, never copy bodies), docs/ideas/README.md
  gains the **B4 frontmatter** convention (no idea files exist yet, so no
  migration). The other three diverged rows are `control/*` — live
  manager/project-owned bus files, correctly left alone.
- **Engagement gate walked RED → GREEN (the stranding fix):** before —
  9 planted docs under UNRENDERED banners, 8 unfilled slots
  (`architecture_layers`, `ownership_model`, `mutation_seam`,
  `new_area_ownership`, `owner_profile`, `review_ritual`,
  `drift_resolution`, `staleness_review`). Answered all 8 with real values
  derived from this repo (layer map from `sb/__init__.py`; seams from
  `sb/kernel/workflow` + the checker fleet; ritual from
  `named-gates.yml` + `.sessions/README.md`; cadence from
  `substrate.config.json`), answered `integration_mode=guided`, confirmed
  the 4 provisional derived slots (`project_name`, `primary_language`,
  `verify_command`, `doc_roots`) — 13/13 slots filled. `render --live`
  filled 9 docs in place, stripped every banner, recorded doc hashes
  (future upgrades can now classify `template-improved` honestly).
  `enforcement-unwired` never fired — ci.yml's `checkers` job already runs
  `check --strict` (the checker's substring contract accepts a hand-rolled
  gate), so the staged `substrate-gate.yml` is deliberately NOT installed:
  a second workflow would double-run the gate and its session-gate step
  is not among the owner's 6 required named checks anyway. `session-loop-idle`
  never fired (real cards exist). KL-8 heartbeat: `control/status.md`
  already carried a parseable `updated:` — overwritten this session per the
  per-session ritual (orders acked=001,002; no done claimed).
- **Verified after:** `bootstrap.py --version` → 1.2.0 via header;
  `check --strict` red **only** on this card's own born-red badge before
  close-out (the gate as designed) — fully ENGAGED otherwise; unit suite
  1064 passed / 1 skipped; manifest_compile + all 21 committed checkers
  green locally (golden-parity gate left to CI's Postgres).

## Kit findings (reported upstream, not worked around)

- **No bugs found this run** — both #46 fixes behave as released. One
  cosmetic observation: the only `archived:` line the verb prints names the
  NEW dist (`bootstrap-1.2.0.py`, from the embedded adopt pass banking the
  running dist for the *next* upgrade); the step-2 OLD-dist archive was
  idempotent-silent because an earlier session had already committed it. A
  reader skimming the output could think the old dist was archived under the
  new version. Suggestion: print `archived: … (already banked)` on the
  idempotent path, or label the adopt-pass line `banked for next upgrade:`.

## 💡 Session idea

The engagement gate proves docs are *rendered*, not that they are *true*:
this session filled `architecture_layers` etc. from source honestly, but a
lazy session could fill slots with plausible filler and go GREEN. A cheap
`check` advisory could cross-check objective slots against ground truth —
e.g. every path token mentioned in `architecture_layers` /
`ownership_model` / `verify_command` must exist on disk (the same
"verifiable output" bar the checker fleet already applies to code). Filed
for the kit; would have caught a hypothetical wrong `sb/…` path here.

## ⟲ Previous-session review

The v1.0.0 upgrade session (PR #46) set the template this session executed
almost verbatim — its best moves were the precise repro it filed for the
from-version bug (config-pin-before-upgrade order) and its 💡 idea (input
self-cleanup): **both shipped in v1.2.0 and both verified here**, a full
consumer→kit→consumer friction loop closing in one day. What it could have
done better: it left the engagement stranding (unrendered docs) unnamed
even though its own `check` output ran across those files — the fleet
review had to find it later. Improvement this surfaces: a session that
touches kit surfaces should end by running the *newest* kit's check against
the tree (not just the vendored one) so next-version gates are anticipated
rather than discovered at upgrade time.

## ⚑ Flags

- Self-initiated: manually merged the three diverged-doc template deltas
  (Program-law pointers + ideas frontmatter) — the report's manual lane,
  additive-only, reversible by git.
- Self-initiated: did NOT install the staged `substrate-gate.yml`
  workflow — ci.yml already wires `check --strict` and the owner's 6-check
  ruleset would treat a new required-name workflow as a settings change;
  documented instead (this card + PR body). Owner can install later if he
  wants the control fast-lane CI behavior on this repo.
- Deviation from the session prompt, deliberate: auto-merge armed as the
  LAST step (after this card flipped complete), not at PR open — this
  repo's `check --strict` runs in the non-required `checkers` job, so a
  born-red card cannot hold auto-merge here; arming at open would repeat
  the #44 premature-merge incident. Friction→guard follow-up filed below.
- Friction: the born-red convention is enforceable only if the session gate
  sits inside a *required* check. Cheapest enforcing fix candidates: pass
  an explicit `--session-log` derived from the PR diff inside one of the 6
  named gates (e.g. `code-quality`), or owner adds `checkers` to the
  required set. Left as a documented decision for the owner (ruleset
  changes are settings, not files).

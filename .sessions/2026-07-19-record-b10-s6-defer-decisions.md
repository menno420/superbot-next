# 2026-07-19 — record B10 route-origin + S6 role-select DEFER decisions

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`), releasing the born-red `substrate-gate` HOLD. First
> commit was this card alone (held the gate red); the two docs landed in the
> second commit; this flip is the last.

- **📊 Model:** opus-4.8 · high · docs-only

## Scope

DOCS-ONLY slice. Record two coordinator decisions (both DEFER, decide-and-flag /
PL-001) into the decisions ledger and flip their routed question-router blocks
from OPEN → ANSWERED (DEFER):

1. **B10 route-origin seam = DEFER.** Adds new kernel surface (a session-scoped
   route-origin signal + a `BACK_TO_ORIGIN` nav mode) for a single cosmetic
   back-button label with no second consumer today; reversible — revisit when a
   second route-origin consumer appears organically.
2. **S6 role-select widget = DEFER.** No reachable role-typed setting exists in
   any non-hub group, so there is no honest golden target to build against;
   build the widget when such a setting exists organically.

Provenance: both decided by the coordinator under decide-and-flag; relayed via
the coordinator session 2026-07-19. Pure reversible DEFERs (the owner had them
routed; the coordinator decided them). No `sb/` code, goldens, or manifests
touched.

## Result

Landed on PR #592 (base main; docs-only). Two docs changed plus this card:

- **`docs/decisions.md`** — appended two ledger entries, matching the file's
  `status / date / verdict / why / provenance` entry shape:
  - **`[D-0098]`** — "B10 route-origin seam stays DEFERRED (no kernel nav-mode
    surface for one back-button label)". Verdict: don't build the
    `opened_from` + `BACK_TO_ORIGIN` seam for one mostly-cosmetic label
    (`role.hub` → "↩ Community" vs "↩ Server Management") with no second
    consumer; a kernel grammar addition earns its keep at ≥2 consumers, and the
    seam permanently adds an origin dimension to every future golden. Reversible;
    revisit slice-1-first when a second route-origin need appears.
  - **`[D-0099]`** — "Settings epic S6 role-select widget stays DEFERRED (no
    reachable honest golden target)". Verdict: no non-hub `input_hint="role"`
    setting is reachable (port declares zero role settings; the oracle's three
    are all unreachable — `moderation.*` unported, `welcome.entry_role` a
    read-only hub with no group_edit page under D-0097 option A), so building S6
    now would ship a speculative dormant widget with no honest golden. Mechanics
    are solved (S5 channel widget with `role` for `channel`); lands in ~1 slice
    once a target exists.
- **`docs/question-router.md`** — the **B10 route-origin go/no-go** and
  **settings epic S6 role-select scoping** blocks flipped **OPEN → ANSWERED
  (DEFER, 2026-07-19)** — status line, `Maintainer answer` (the DEFER verdict +
  a one-line rationale + the coordinator-relay provenance), and `Routing result`
  all updated — and both blocks moved from Open questions into the Answered
  section (the file's convention: "Unanswered Q-blocks live here until the
  maintainer decides"). Bumped the Open-questions header count **three → one**:
  only the **D2 real-time minigame-framework go/no-go** block stays open. The
  **xp negative-level guard** question is untouched — verified it is not carried
  in `question-router.md` at all (grep-checked), so there was nothing to leave
  OPEN there; it stays routed wherever it lives.

**Stamp-gate held.** Each new D-NN id lives in AT MOST ONE non-ledger doc: the
`D-0098` / `D-0099` tokens appear in `docs/decisions.md` ONLY. `question-router.md`
refers to each decision in prose ("recorded in the decisions ledger 2026-07-19")
without the token, and no B10/S6 design doc was touched. Verified:
`grep -rnE 'D-00[0-9][0-9]' docs/ --include='*.md' | grep -v docs/decisions.md`
returns the two new ids in **zero** non-ledger docs.

**Decision flagged (decide-and-flag, PL-001):** placed the two answered blocks
at the TOP of the Answered section (newest-first, above the 2026-07-18 settings
option-A entry) rather than appending them at the tail — the section reads
newest-first and the header narrates "moved to Answered below", so top-of-section
keeps the chronology honest. Reversible re-order if the owner prefers append.

## Verification

- `python3 -m pytest -q --ignore=examples` → **3589 passed, 37 skipped, 1
  warning** in 84s. The 1 warning is the pre-existing `discord/player.py`
  `audioop` DeprecationWarning (stdlib, unrelated). Exit 0.
- `python3 bootstrap.py check` → **exit 0** both before and after the card flip
  (decisions.md + question-router.md reachable; stamp-gate clean — the gate that
  would fail if a D-NN spread to a 2nd non-ledger doc). The only card note
  ("missing Session idea / Previous-session review / completed Status") was the
  born-red hold on THIS card, cleared by this flip.
- `git diff --name-only origin/main` → `.sessions/2026-07-19-record-b10-s6-defer-decisions.md`,
  `docs/decisions.md`, `docs/question-router.md` (+ `.substrate/guard-fires.jsonl`
  telemetry). No code, goldens, or manifests touched.
- **Guard-fires delta:** `python3 bootstrap.py check` appended **advisory-only**
  records to `.substrate/guard-fires.jsonl` (`posture: advisory`, never
  exit-affecting) — the pre-existing `owner-action-fields` (control/status.md),
  `claims-format` ×3, `seat-digest-stale`, `automerge-branch-drift` conditions
  plus the born-red `session-log` note on this card. **Zero** new
  guard/gate-breaking fires from this slice; committed with the session per the
  check's "commit the delta — do not revert" instruction.

## 💡 Session idea

These two DEFERs are the same shape wearing two disguises, and naming the shape
is the reusable insight: **a build earns its infrastructure only when a second,
independent consumer exists — and "consumer" means something different in each
case, which is exactly what makes the rule feel like two rules until you see it
is one.** B10's missing second consumer is a *surface that needs the kernel
grammar* (one more routed manager or breadcrumb that wants a dynamic back
label); S6's missing second consumer is a *setting the widget can honestly
render* (one reachable non-hub `role` setting). Both proposals are mechanically
solved and cheap to build — B10's slice 1 is zero-golden-churn, S6 is the S5
widget one hint over — so the temptation in both is to build now because the
code is easy. The rule resists exactly that temptation: cheap-to-build is not
the same as earns-its-keep, and the honest gate is *a second real consumer*, not
*low cost*. The corollary the pair makes sharp: **you do not manufacture the
second consumer to justify the first** — for B10 that would be opting a contrived
panel into route-origin; for S6 that would be adding a role setting to a non-hub
group purely to feed the widget's golden. Fabricating the consumer inverts the
rule (the infra now justifies the consumer instead of the reverse), which is why
both defers are *reversible waits for organic arrival*, not rejections. The DEFER
verdict is the disciplined default whenever a clean, additive, one-consumer build
is on the table: shelve the plan intact, and let the second need pull it in.

## ⟲ Previous-session review

This slice is the direct downstream of two routing sessions, and reviewing them
together is the honest close-out. **`2026-07-18-b10-decision-ready-plan.md`**
turned B10 into an "executable-pending-one-decision" package: it filed the
implementation plan and routed a single crisp go/no-go with a **recommended
DEFAULT of DEFER (leaning GO-when-a-second-need-appears)** — and, notably, it
minted **no** `D-00NN` token, routing through the router's native `### Q:`
convention precisely to avoid cross-doc stamp bleed. That restraint is what made
today's stamp-gate trivially clean: the go/no-go carried no id to leak, so this
session could mint `D-0098` in the ledger alone and refer back in prose. The one
thing that card could not do — and correctly did not — was decide; it left the
cost/benefit call to the owner, and the coordinator has now made it, matching the
card's own recommended default. **`2026-07-19-settings-s6-role-question.md`** did
the same for S6: it routed the reachability question (recommended DEFER) and its
own session idea already isolated the real blocker — S6 is "mechanically solved
yet un-buildable" because it lacks a *reachable* honest target, a two-layered
absence (port-coverage for `moderation`, product-decision for `welcome` under
option A). Today's decision ratifies that read exactly. Both predecessors were
scrupulous about the OPEN/ANSWERED boundary — routing, never deciding — and that
discipline is what let this session be a clean, low-risk ledger-and-flip with no
re-litigation: the analysis was already done and honest; only the verdict was
missing.

# 2026-07-18 — settings group_pending epic plan: land option-A owner decision + executable slice plan

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`), releasing the born-red `substrate-gate` HOLD. First
> commit was this card alone (held the gate red); the two docs landed in the
> second commit; this flip is the last.

- **📊 Model:** opus-4.8 · medium · docs-only

## Goal

Land ONE contained docs-only slice recording the now-made owner decision on the
`settings.group_pending` per-group scalar-edit page, and turning the scoped
epic into an executable clean-slice plan:

1. `docs/question-router.md` — mark the OPEN settings per-group edit-page
   group-routing question (appended in #558) ANSWERED with the maintainer's
   **option A** ruling: the ported edit page replaces `group_pending` for the
   **non-hub groups only**; the 5 operator-spine hub groups
   (welcome / counters / security / automod / image_moderation) keep routing
   to their `<group>.hub`. Record the provenance line and route the answer
   into the new plan doc.
2. `docs/design/settings-group-pending-epic-plan.md` — a NEW planning doc: the
   S0→S7 slice breakdown for the settings-mutation epic, built onto the
   existing seams, incorporating the option-A decision.

## Scope

Docs-only. Two docs (+ a design/README.md reachability row) + this card. No
`sb/` code touched. No decision-ID (`D-00NN`) token minted (the file's native
token is `Q-`; concrete answered entries carry descriptive `### Q:` titles
without own numbers).

## Provenance

Owner directive relayed via the coordinator session on 2026-07-18 (~21:20Z):
**option A** — edit page for non-hub groups only; the 5 hub groups unchanged.
Per the never-wait rider, silence = consent; this is a decide-and-flag record
(PL-001).

## Verification (re-confirmed at HEAD this session)

- **Routing divergence re-read:** `sb/domain/settings/handlers.py` keeps its
  three-way `open_group` branch — `_GROUP_PANELS` (`:37`, `:269`, `games` →
  `games.sections`), `has_operator_hub` (`:272`, the 5 operator-spine hubs), and
  the `group_pending` BLOCKED fallthrough (`:242` registration, `:277`). Option
  A wires the edit page into the third arm ONLY; the first two arms are
  untouched. The 5 hubs are the `ensure_hub(...)` subsystems in
  `sb/manifest/{welcome,counters,security,automod,image_moderation}.py`.
- **Seams confirmed present:** `SET_SCALAR` / `CLEAR_SCALAR` K7 ops
  (`sb/domain/settings/ops.py:264` / `:277`); `ModalSpec`/`ModalFieldSpec` +
  `defer_mode==MODAL` G-10 invariant (`sb/spec/panels.py:243/258/310`);
  windowed selects (`sb/kernel/panels/selectwindow.py`); the already-ported
  `edit_command_access.py` widget lives in `handlers.py:412+` over
  `sb/domain/platform/command_access.py` with `_ACCESS_SESSIONS` state
  (`handlers.py:47`).
- **pytest:** `python3 -m pytest -q --ignore=examples` → **3481 passed, 29
  skipped, 1 warning** (docs-only; `examples/` excluded per the standing
  plugin-example import gap).
- **docs-gate:** `python3 bootstrap.py check` → **all checks passed** — the new
  `docs/design/settings-group-pending-epic-plan.md` carries the `plan` Status
  badge in its first ~12 lines and is reachable (linked from
  `docs/design/README.md`'s production-readiness table). No unreachable/badge
  finding for the new doc. Pre-existing advisory warnings only (owner-action /
  claims / seat-digest / automerge-drift / model-line-class on OTHER cards) —
  none mine, none exit-affecting.

## Trail

- **question-router.md:** filled the OPEN block's `Maintainer answer` with the
  option-A ruling + provenance, and the `Routing result` pointing at the new
  plan doc; changed the Status field `OPEN` → `ANSWERED (option A, 2026-07-18)`;
  MOVED the block out of "Open questions" into "Answered" (removed the now
  duplicate `## Answered` header) so the section invariant holds; rewrote the
  Open-questions header note from "One unanswered block below…" to "No
  unanswered blocks…". No other blocks touched.
- **settings-group-pending-epic-plan.md:** new plan doc — owner-decision scope
  gate (the three-arm routing table, option A wires only the non-hub arm),
  the four existing seams to build onto, S0 (page frame) + S1–S7 (bool / enum /
  number-modal / text-modal / channel / role / numeric-presets) each with
  deliver / oracle-port / seam / golden, and a risks section (one golden per
  widget; no single group is pure-bool so S0 type-dispatches once ≥2 widgets
  land; the option-A boundary is load-bearing; `group_pending` retirement is
  one-way per group; record the decision in `decisions.md` on first landing).
- **design/README.md:** added the doc's row to the production-readiness table
  (reachability wire).
- No `sb/` code touched — this is a PLAN (decide-and-flag), not built code; it
  makes the epic executable as future clean slices.

## 💡 Session idea

The one already-ported edit widget (the oracle's `edit_command_access.py`)
landed as ~300 lines fused **inside** `sb/domain/settings/handlers.py`
(`:412+`), not as its own module — so the S1–S7 widget slices have no seam
boundary to slot into and will keep growing that one handlers file. A cheap
pre-S0 refactor (extract the command-access editor into
`sb/domain/settings/widgets/` and make S0's page frame import widgets from
there) would give every later slice a clean per-widget home and keep the
per-slice diffs reviewable. Guard recipe: watch `sb/domain/settings/handlers.py`
line count against a soft ceiling in `tools/` (the settings band already has
`tests/unit/settings_band/`); a widget added inline instead of under a
`widgets/` package is the smell to flag.

## ⟲ Previous-session review

The 2026-07-18 flip-mining-rows-route-settings session (`complete`, #558) did
the disciplined groundwork this slice builds on — it caught that #556's report
CLAIMED a question-router routing that never landed and actually appended the
OPEN block, so the decision had a real home to answer into; a good reminder
that "routed to X" is only true once X's bytes exist, which is exactly the
condition this session could rely on because #558 verified it.

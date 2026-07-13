# 2026-07-13 — setup wizard successors slice 1: the final-review apply lane

> **Status:** complete

- **📊 Model:** Fable · setup-wizard successor lane, slice 1

## Scope

Port the oracle final-review apply lane (menno420/superbot
`disbot/views/setup/final_review.py` — FinalReviewView + ApplySummary +
PartialApplyRecoveryView + SetupCompleteView, plus the provisioning
preview/confirm panels' posture) onto superbot-next's panel/handler/K9
idiom: render the final-review card from the staged K9 draft ops, arm
the gated Apply that executes staged ops through the audited kernel
seams (DraftPipeline over the registered `bind_channel` → `settings.bind`
op kind), the apply summary, partial-apply recovery, and the
setup-complete view; flip the `setup.open_section_final_review` honest
BLOCKED terminal into the lane. Essential steps 2–8, the other 9 section
flows, and the suggestion Edit lane keep their honest terminals
untouched. Golden-pinned OPEN renders stay byte-identical.

## 💡 Session idea

The K9 `PARTIAL` draft status is terminal, but the oracle's recovery
contract needs a re-runnable remainder — this slice re-stages the
failed/skipped ops into a fresh OPEN draft at apply time. A kernel-lane
`DraftPipeline.reopen_partial(draft_id)` (CAS PARTIAL→OPEN keeping op
rows + dedup tokens) would make recovery first-class, preserve the
once() idempotency keys across retries, and retire the re-stage
workaround here and in the future preset/AI-orchestration recovery
surfaces.

## ⟲ Previous-session review

The previous lane session (wizard-lifecycle slice,
`.sessions/2026-07-13-setup-wizard-interior.md`, PR #340) made this
successor easy to locate: its honest-terminal pattern named the
final-review apply lane in four places (wizard.py docstring, the
review_stage confirmation copy, panels.py, the completeness table), so
finding the exact flip points took minutes, not archaeology. Its K9
staging lane (`stage_accepted` + the `bind_channel` op-kind
registration) was already apply-shaped — the ONE op kind this slice
executes was pre-bound to `settings.bind`, which is the strongest
evidence the honest-successor discipline pays forward.

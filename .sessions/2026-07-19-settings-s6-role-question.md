# 2026-07-19 — settings epic: route S6 role-select open question + epic wrap-up

> **Status:** `in-progress`

- **📊 Model:** [[fill: family · effort · kind]]

## Scope

DOCS-ONLY slice. The settings `group_pending` per-group scalar-edit-page epic
(`docs/design/settings-group-pending-epic-plan.md`) is essentially complete: S0
(page frame) + S1 bool + S2 enum + S3 number-modal + S4 text-modal + S5
channel-select + S7 numeric-presets have all landed or are landing (PRs
#579–#584). The ONE remaining slice, **S6 (role-select)**, is genuinely blocked
and must be ROUTED as an open question, NOT built.

Why S6 is blocked (verified this session):
- The S6 role widget needs a REACHABLE, honest golden target: a NON-HUB group
  setting with `input_hint="role"` that routes to the `settings.group_edit`
  page.
- superbot-next declares ZERO role settings today — `rg 'input_hint="role"' sb/`
  returns nothing.
- The oracle (`menno420/superbot @ f87fa508`) has 3 role settings:
  `moderation.moderator_role`, `moderation.trusted_tier_role` (moderation is NOT
  a ported group_edit subsystem in the port), and `welcome.entry_role` — but
  `welcome` is one of the 5 read-only operator-spine HUB groups, which under the
  epic's option-A decision (`docs/question-router.md` → Answered, 2026-07-18)
  have NO group_edit edit page, so `welcome.entry_role` is UNREACHABLE by the S6
  widget.
- Net: no reachable, honest role-setting target exists today. Introducing one
  (adding a role setting to some non-hub group) is a product/scoping call, not
  mechanical porting. Per the epic's "no speculative widgets without an honest
  golden" rule, S6 must not be built as dormant infra.

Deliverables:
- `docs/question-router.md`: a new OPEN Q-block routing the S6 scoping question
  (options A introduce-a-role-setting / B defer — recommend B), citing the epic
  plan and the option-A Answered block.
- `docs/NEXT-TASKS.md`: an epic wrap-up note — the settings.group_pending
  edit-page epic is COMPLETE for all reachable scalar types
  (bool/enum/number/text/channel/presets); the only open item is S6 role-select,
  blocked on the routed scoping question; `group_pending` fully retired.
- NO code, goldens, or manifests touched. `git diff --name-only origin/main`
  must list only `docs/` + `control/claims/` + `.sessions/` files.

## Result

[[fill: on flip to complete]]

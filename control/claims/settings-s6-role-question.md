# Claim — settings-s6-role-question

- `claude/settings-s6-role-question` · **settings epic — route S6 role-select
  open question + epic wrap-up.** DOCS-ONLY. The settings `group_pending`
  edit-page epic (`docs/design/settings-group-pending-epic-plan.md`) is complete
  for every reachable scalar type (S0 frame + bool / S2 enum / S3 number-modal /
  S4 text-modal / S5 channel-select / S7 numeric-presets). The one remaining
  slice, **S6 (role-select)**, is genuinely blocked: superbot-next declares ZERO
  `input_hint="role"` settings, and the oracle's three role settings
  (`moderation.moderator_role`, `moderation.trusted_tier_role`, `welcome.entry_role`
  @ `menno420/superbot f87fa508`) are all unreachable by the S6 widget —
  `moderation` is not a ported group_edit subsystem, and `welcome` is one of the
  5 read-only operator-spine HUB groups that under the epic's option-A decision
  have NO group_edit edit page. Per the epic's honest-golden rule (no speculative
  widget without a reachable oracle-replay target), S6 must NOT be built as
  dormant infra — it is ROUTED as an open question instead. This slice (a) adds a
  question-router OPEN block asking how to proceed on S6, and (b) records the
  epic wrap-up in `docs/NEXT-TASKS.md` (epic complete for all reachable scalar
  types; `group_pending` fully retired; S6 the sole open item). No code, goldens,
  or manifests touched. · files: `docs/question-router.md`, `docs/NEXT-TASKS.md`,
  `control/claims/settings-s6-role-question.md`,
  `.sessions/2026-07-19-settings-s6-role-question.md` · 2026-07-19

# 2026-07-13 — curation night bundle 2: btd6.ctteam set-team guided flow (ORDER 019 item 2)

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · night lane worker · mandate: ORDER 019 item 2 (curation REWORK backlog, `docs/review/curation-report-2026-07-13.md` row 2 `btd6.ctteam.set_team`, ~L377) · claim: `control/claims/curation-rework-night-bundle.md` (PR #426)

## Scope

Row 2 of the curation REWORK backlog: `btd6.ctteam.set_team` routes to the
`btd6.ctteam_set_pending` terminal (`sb/domain/btd6/panels.py:344`) while the
oracle has the button live-wired to the guided CT-team flow (Settings Phase 2,
Q-0064: URL/id → parse → preview → confirm, never a raw scalar write). Port
the flow onto the plugin/manifest architecture and retire the pending:

- G-10 modal (`Set CT team` / "CT bracket URL or id") on the existing
  `btd6.ctteam` set_team action — the PR #375 / #358 modal-ingress precedent;
- `parse_group_id` + preview/confirm step verbatim from oracle
  `disbot/services/btd6_ct_team_service.py` + `disbot/views/btd6/ct_group_flow.py`;
- ONE audited write through a new `btd6.set_ct_team` K7 op (legacy-KV
  `guild_settings.btd6_ct_group_id`, the `btd6.set_announce_channel` twin);
- arm the typed `!btd6 ctteam <arg>` set/clear leg onto the same flow
  (`sb/domain/btd6/oracle_surface.py:cmd_ctteam` — its BLOCKED byte retires
  with the pending).

Live NK bracket standings stay the D-0046 ingestion successor — the preview
renders the shipped no-active-event byte, which is this build's true state.

## Previous-session review

[[fill: close-out]]

## What shipped

[[fill: close-out]]

## 💡 Session idea

[[fill: close-out]]

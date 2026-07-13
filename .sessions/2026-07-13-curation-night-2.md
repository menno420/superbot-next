# 2026-07-13 — curation night bundle 2: btd6.ctteam set-team guided flow (ORDER 019 item 2)

> **Status:** `complete`

- **📊 Model:** `fable-5` · night lane worker · mandate: ORDER 019 item 2 (curation REWORK backlog, `docs/review/curation-report-2026-07-13.md` row 2 `btd6.ctteam.set_team`, ~L377) · claim: `control/claims/curation-rework-night-bundle.md` (PR #426)

## Scope

Row 2 of the curation REWORK backlog: `btd6.ctteam.set_team` routed to the
`btd6.ctteam_set_pending` terminal (`sb/domain/btd6/panels.py:344`) while the
oracle has the button live-wired to the guided CT-team flow (Settings Phase 2,
Q-0064: URL/id → parse → preview → confirm, never a raw scalar write). Port
the flow onto the plugin/manifest architecture and retire the pending.

## Previous-session review

Boot recon (this lane's own scratchpad boot report) found the order's "next
~17 of 27" backlog stale — 21 rows already shipped; row 2 was one of 6 real
residues. The shipped precedents held up cleanly as templates: #358's modal
ingress + born-red card shape, the cleanup policy_widgets page-swap posture
for confirm flows, and the `btd6.set_announce_channel` op as the exact
legacy-KV write twin. One friction: the completeness table's btd6 row cited
the pending by a stale line number (`oracle_surface.py:623`) — anchors in
status docs drift fast; citing the symbol, not the line, would age better.

## What shipped

PR #428, branch `claude/curation-night-2`. The guided flow, oracle-verbatim
(`disbot/services/btd6_ct_team_service.py` + `views/btd6/ct_group_flow.py` +
`cogs/btd6/_builders.handle_ctteam` @9c16365):

- `sb/domain/btd6/ct_team.py` (new): `parse_group_id` verbatim (hex 8–64,
  `/group/` URL tail, query/fragment strip, lower-fold), the modal-submit /
  confirm / cancel handlers, the presentation-lane settings read (degrades
  to `""` — a view never requires the DB). Deviations ledgered in-module
  (page-swap instead of edit-in-place; one panel visibility; live NK
  standings stay D-0046 — the no-active-event byte is this build's truth).
- `btd6.ctteam_set_form` G-10 modal on the existing set_team action
  (label/emoji/row bytes unchanged — sweep_btd6_ctteam golden safe);
  `btd6.ctteam_confirm` session page (Confirm/Cancel, author-locked 180s,
  staff-tier Confirm re-check) with the preview embed (Change/Bracket-id +
  ` • ctx=btd6_ct:confirm` footer).
- ONE audited write: `btd6.set_ct_team` K7 op (staff floor, legacy-KV
  `guild_settings.btd6_ct_group_id` upsert — the announce-channel twin);
  set writes the parsed id, clear writes `""`.
- Typed leg armed: `!btd6 ctteam <url-or-id>` → preview+confirm; `clear`
  immediate + audited; DM guard, permission notice, mis-paste refusal —
  copy verbatim; the no-arg view now shows the configured pointer.
- Retired: `btd6.ctteam_set_pending` (handler + registration gone).
- Verification: full suite 2911 passed / 15 skipped on the merged tree;
  `bootstrap.py check --strict` clean except the designed born-red hold
  (this card, flipped in this commit); compat pin grew exactly the modal
  root; snapshot recompiled byte-stable post-merge.
- Tests: `tests/unit/band7/test_band7_btd6_ctteam_flow.py` (20 cases —
  parser, spec shapes, card bytes, handler copy, op shape, never-writes
  guards).

## Guard recipe

`RenderedEmbed` has a REQUIRED positional `description` — a fields-only
card (`ctteam_confirm_card`, sb/domain/btd6/oracle_cards.py) must pass
`description=""` explicitly; the TypeError only fires at call time, so a
new card builder needs a construction smoke test before the suite run
(test: `test_confirm_card_change_line_and_footer`).

## 💡 Session idea

The curation report's REWORK rows cite evidence as `file.py:NNN` line
anchors frozen at report time; three shipped bundles later the numbers
drift (row 2's `panels.py:298` was `:344` at my HEAD). A tiny
`tools/check_report_anchors.py` that greps each cited symbol (not line)
and emits a drift map would let night workers trust the report without
re-deriving locations — and could auto-annotate rows already shipped,
which is exactly the staleness that inflated this order's "~17 rows".

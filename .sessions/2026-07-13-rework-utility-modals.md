# 2026-07-13 — curation rework: utility panel Poll/Remind modal ingress

> **Status:** `complete`

- **📊 Model:** `fable-5` · curation rework lane (ORDER 017 item 2 successor;
  evidence: `docs/review/curation-report-2026-07-13.md` L1356-1357 +
  consolidated backlog L1557) · mandate: arm the utility panel's 📊 Poll and
  🔔 Remind Me buttons via G-10 modal ingress onto the LIVE command-twin
  lanes, retiring the two pending terminals

## Scope

The curation report's two REWORK rows for `utility.panel`: both buttons
route to pending terminals (`utility.poll_pending`,
`utility.remind_pending`, sb/domain/utility/handlers.py:464-465) while the
command twins are live and golden-backed — `!poll` (`utility.poll_view`,
handlers.py:354, golden sweep_poll.json) and `!remind`
(`utility.remind_view`, handlers.py:375, golden sweep_remind.json). Rework:
each button opens a declared ModalSpec (the moderation/general G-10
precedent) whose submit normalizes the form fields into the SAME code path
the command twin runs — shared outcome helpers extracted from the
argv-shaped views, no duplicated parsing/formatting, no new egress
capability (poll's valid lane still ends on the honest `_POLL_DOWN`
refusal; remind's on the pinned ack copy). The two pending registrations
retire. Wire bytes stay golden-pinned verbatim (labels/styles; session
panels mint `<cid:N>` ids) — no golden re-cut; the snapshot recompiles for
the handler/modal manifest change.

Adjacency: PR #332 (claude/curation-rework-nav-wiring) touches the SAME
`sb/domain/utility/panels.py` row-1 region for the Invite one-liner — this
lane does not touch the invite lines or the row-1 lead comment.

## Close-out

- `sb/domain/utility/panels.py` — `POLL_MODAL` (`utility.poll_form`:
  question + one-per-line PARAGRAPH options) and `REMIND_MODAL`
  (`utility.remind_form`: minutes + message — the moderation
  TIMEOUT_MODAL "minutes" family); the poll/remind PanelActionSpecs
  carry `defer_mode=MODAL` + the forms, handlers →
  `utility.poll_submit` / `utility.remind_submit`. The invite lines and
  the row-1 lead comment left byte-untouched (PR #332's hunks).
- `sb/domain/utility/handlers.py` — poll_view/remind_view refactored
  onto shared `_poll_outcome`/`_remind_outcome` (one copy of every
  guard + reply byte); the two submits normalize field_ids into the
  same lanes. `utility.poll_pending`/`utility.remind_pending` +
  `_REMIND_DOWN` retired.
- `manifest.snapshot.json` recompiled — exactly the two handler swaps,
  `defer_mode` auto→modal, and the two modal bodies (rebased over the
  fishing slice-4 snapshot move; conflict resolved by recompile).
- `tests/unit/band6/test_band6_utility_modals.py` — 13 tests: spec/
  compile/layout fences, retirement sweep, and submit-vs-command-twin
  byte parity on every guard lane (valid, malformed duration, zero
  minutes, blank message, <2/>10 options, blank question).
- Gates: pytest **2213 passed / 13 skipped**; manifest_compile green
  (48 manifests); check_schema_growth clean; full ci.yml checker fleet
  clean; `bootstrap.py check --strict` exit 0 (mining-lane claims
  advisory known-OK); parity gate **GREEN — all 484 goldens across 51
  subsystems replay clean** (the four utility panel/tool sweeps
  byte-unchanged — no golden re-cut).

## 💡 Session idea

The poll modal's valid lane still ends on the honest `_POLL_DOWN`
refusal — the rework armed the INGRESS, not the reaction-egress port.
When that port arms, `_poll_outcome`'s final return is the single line
to replace (both surfaces inherit it) — a one-line guard recipe worth
more than re-deriving the twin-delegation topology. Same shape for
remind: `_remind_outcome`'s SUCCESS ack is where the timed-delivery
spawn lands.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-anchor-sweep-design.md`.) A docs-only
lane, but two of its habits paid here: (1) re-verify every claimed
citation at HEAD before building — this session re-checked the two
pending refs and found PR #332 editing the SAME panels.py row-1 region,
which shaped the hunk-avoidance posture (invite lines + lead comment
untouched); (2) its "stamp discipline" instinct — one home per fact —
mirrored this lane's one-copy-per-guard refactor (the shared outcome
helpers exist so the modal and command never fork their reply bytes).
Its 💡 (a `proposed` badge for pre-decision docs) is untouched by this
session — still open for the kit.

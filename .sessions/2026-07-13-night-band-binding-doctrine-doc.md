# 2026-07-13 — night: band-binding doctrine + effect-arming compensator checklist (doc-only)

> **Status:** `complete`

- **📊 Model:** `fable-5` · ORDER 019 item 8 `[build-direct]` · claim:
  control/claims/night-money-race-and-doctrine-doc.md (PR #422, branch
  pre-declared `claude/night-band-binding-doctrine-doc`)

## Scope

One doc-only PR to `docs/collaboration-model.md`: encode (a) the ORDER 004
band bindings (walking-skeleton live-drive · classify-or-fix · demo rule) and
(b) the EFFECT-arming compensator checklist as standing doctrine sections
beside the ORDER 010 @codex rule — giving ORDER 004 its `done=` citation hook.

Sources (read-only): idea-engine
`ideas/superbot-next/band-binding-doctrine-encoding-2026-07-10.md` and sibling
`ideas/superbot-next/effect-arming-compensator-checklist-2026-07-10.md`, both
@ `2e5d73f`.

## Close-out

Landed as PR #427 (head at flip: doc commit `c6d881c`). Two sections added
beside § Standing @codex review: **§ Band bindings (ORDER 004, standing)**
(three bindings + the close-out citation hook) and **§ EFFECT-arming
checklist (standing)** (four arming checkboxes + the EMPTY-allowlist
rationale). Doc-only diff; Status `binding` badge intact at line 3;
reachable via docs/AGENT_ORIENTATION.md planted-doc router.
Verify: `python3 -m pytest tests/ -q` → 2867 passed, 15 skipped;
`python3 bootstrap.py check --strict` → green minus this card's own
designed born-red hold (this flip clears it). No self-merge — auto-merge
armed by the enabler.

- 💡 The EFFECT-arming checklist's four checkboxes are PR-body discipline a
  checker could partially see: a cheap CI advisory that flags any PR touching
  `sb/**/ops.py` effect-leg registrations without the literal phrase
  "compensates-nothing ruling" or a `compensate_` ref in the diff would turn
  half the checklist from exhortation into enforcement (PL-007), without
  over-mechanizing the judgment halves.
- **previous-session review:** `.sessions/2026-07-13-setup-compound-1.md`
  (PR #419) — clean card: scope names the two K7 compound ops with their
  oracle pin (menno420/superbot @ f969b95) and the D-0077 get-before-create
  rationale, and the close-out records the bind-failure-does-not-undo and
  threshold-fold-best-effort semantics explicitly, which is exactly what a
  successor arming those channels/roles live will need; its "bootstrap check
  green minus this card's own designed born-red hold" phrasing is the same
  hold pattern this card rides, confirming the convention is stable across
  seats.

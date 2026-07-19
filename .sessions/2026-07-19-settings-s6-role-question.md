# 2026-07-19 — settings epic: route S6 role-select open question + epic wrap-up

> **Status:** `complete`

- **📊 Model:** opus · high · docs-only

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

Routed S6 and recorded the epic wrap-up on PR #585 (base main; docs-only). Two
docs changes plus the claim + this card:

- **`docs/question-router.md`** — appended a new OPEN block, "settings epic S6
  (role-select edit widget) — no reachable honest golden target exists; how to
  proceed?", in the Open-questions section (matched the existing `### Q:` /
  `Area·Type·Priority·Status` / `Question` / `Why agents need this` / `Options`
  / `Recommended default (my read)` / `Maintainer answer: (pending)` /
  `Routing result: (pending …)` field shape used by the live B10 + D2 blocks).
  The block carries the verified blocking facts (0 port `input_hint="role"`
  settings; the oracle's 3 role settings all unreachable — `moderation.*`
  unported, `welcome.entry_role` a read-only hub with no group_edit page under
  option A) and the two options: **(A)** introduce/port a role setting into a
  non-hub group that routes to group_edit, then build S6 with an honest golden;
  **(B) DEFER** (recommended) until a role-typed non-hub setting exists
  organically. Cites the epic plan and the option-A Answered block. Also bumped
  the Open-questions count note from "Two unanswered blocks" to "Three".
- **`docs/NEXT-TASKS.md`** — added an epic wrap-up note under build-backlog
  item 1 (the port-to-parity item the epic belongs to): the settings
  `group_pending` edit-page epic is COMPLETE for every reachable scalar type
  (S0 frame + bool / enum / number / text / channel / presets, PRs #579–#584);
  `group_pending` is fully retired for every non-hub group; the sole open item
  is S6 role-select, blocked on the routed scoping question (linked).

Diff is docs-only — `git diff --name-only origin/main` lists exactly
`docs/question-router.md`, `docs/NEXT-TASKS.md`,
`control/claims/settings-s6-role-question.md`, and this card. No code, goldens,
or manifests touched. `python3 bootstrap.py check` passes (only advisory
never-exit-affecting warnings; the born-red card's "missing idea/review/fill"
gate note cleared on this flip). The local check regenerated
`.substrate/guard-fires.jsonl` (kit telemetry) — reverted, since it is not part
of this docs-only slice.

**Decision flagged (decide-and-flag, PL-001):** placed the S6 wrap-up note as a
sub-bullet of NEXT-TASKS item 1 rather than minting a new top-level backlog
item — the epic is a port-parity sub-effort, and item 1 is where the
port-parity ledger lives, so a new numbered item would over-weight a
single-slice-remaining epic. Reversible one-line move if the owner prefers a
standalone item.

**Mid-task correction (flagged):** origin/main advanced from `7c083796` (S5
merge, my branch point) to `679a7e7` (S7 #584 merge) while this slice was in
flight, so the pre-flip `git diff --name-only origin/main` transiently showed
S7's presets + code files as "missing" from my branch. Rebased the branch onto
the new origin/main (clean, no conflicts) so the docs-only claim holds against
the *current* main — S7's work is now in my base, not my diff.

## 💡 Session idea

S6 is the epic's cleanest proof that a slice can be *mechanically solved yet
un-buildable* — and the two blockers are of different kinds, which is the
insight worth pinning. The widget CODE is trivial: S6 is the S5 channel widget
with `role` swapped for `channel` (a windowed select → `set_scalar`), one
dispatch arm the S7 card already predicted would sit under `PANEL_FLOOR`. What
blocks it is not engineering but the absence of an **honest golden target**, and
that absence is itself two-layered: `moderation`'s role settings are blocked by
a **port-coverage** boundary (the subsystem isn't ported), while `welcome`'s is
blocked by a **product-decision** boundary (option A gives hub groups no
group_edit page). The port-coverage gap could close on its own as more
subsystems land; the option-A gap will not — it is a ruling, not a backlog item.
So the general rule the epic surfaces: *a widget slice needs three independent
things to be buildable — solved mechanics, a type-matching setting, and that
setting being **reachable** by the surface under the current routing ruling* —
and a slice can have the first two and still be honestly un-shippable on the
third. The right move for such a slice is to route the reachability question, not
to fabricate a target to satisfy the mechanics. That is exactly why S6 becomes a
question-router block instead of a dormant widget: building it would trade the
epic's honest-golden rule for a green-looking but target-less slice.

## ⟲ Previous-session review

S7 (numeric-presets, #584) closed the epic's last *buildable* widget and its
card did S6 a real favor by predicting, precisely, that S6 "will NOT need to
[touch `settings.lock.json`] — it is back under the [PANEL_FLOOR] floor" (a
single native picker, not a variable-arity button grid). That prediction holds
and sharpens this routing call: it confirms S6's block is purely the missing
honest target, not any lurking sim-gate or compat-frozen cost — so the moment a
reachable role-typed non-hub setting exists, S6 really is the ~1-slice drop-in
the router block promises. The one thing S7's card understated: it framed S6 as
merely "back under the floor" (a mechanics observation), without flagging that
S6 has **no reachable setting to render at all** — the arity was never the
blocker; reachability was. This slice records that missing half so the epic's
completeness picture is honest: six widgets done, one *routed*, none pending on
mechanics.

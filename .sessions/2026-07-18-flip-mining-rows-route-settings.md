# 2026-07-18 — flip B2/B3 mining rows DONE, route the settings per-group edit-page owner decision

> **Status:** `complete`

- **📊 Model:** opus-4.8 · medium · docs-only

## Goal

Land one contained docs-only slice that fixes two stale artifacts the prior
07-18 reconcile (#556) missed:

1. `docs/status/completeness-table-2026-07-18.md` still lists **B2** (mining
   skill-panel spend) and **B3** (mining workshop craft selector) as OPEN /
   MINTABLE, but BOTH already landed on main — #556 flipped C1 + the wizard
   doc-fix but left these two mining rows stale.
2. `docs/question-router.md` has no entry for the `settings.group_pending`
   per-group scalar-edit-page owner decision, even though #556's report
   CLAIMED to route it there — the routing never actually landed.

## Scope

Docs-only. Two files:
- `docs/status/completeness-table-2026-07-18.md` — flip B2 + B3 OPEN → DONE,
  move them into the DONE / NOT-A-GAP section (same shape as #556's C1 flip),
  citing PR #527 (B2) and PR #532 (B3). No other rows touched.
- `docs/question-router.md` — append ONE properly-formatted owner-intent entry
  for the per-group edit-page group-routing decision. No decision-ID token.

Plus this card. No `sb/` code touched.

## Verification (re-confirmed at HEAD this session)

- **B2 DONE at HEAD:** `sb/domain/mining/panels.py:797-811` routes the four
  `sk_*` buttons to `mining.skill_spend_route` (not the old
  `mining.skill_spend_pending` the table cited); golden
  `parity/goldens/mining/mining_skill_spend_write.json` +
  `tests/unit/mining/test_mining_skill_spend_button.py` both present.
  `git log -1 1e61fe6` → "mining: port 🌳 skill-tree per-branch spend buttons
  to the oracle (B2) (#527)".
- **B3 DONE at HEAD:** `sb/domain/mining/panels.py:1240-1241` wires the
  `ws_craft` selector to `mining.workshop_craft_pick` (handler `:1172-1242`);
  golden `mining_workshop_craft_write.json` +
  `tests/unit/mining/test_mining_workshop_craft.py` present. `git log -1
  cae15f8` → "mining: port 🔧 Workshop gear-craft select to the oracle (B3)
  (#532)".
- **question-router gap re-confirmed before writing:** `grep -ni
  'group_pending\|per-group edit' docs/question-router.md` at HEAD returned
  nothing — #556's report claimed it routed the owner decision there, but the
  block was never appended.
- **Port-vs-oracle divergence re-read:** `sb/domain/settings/handlers.py`
  registers the `settings.group_pending` terminal (~`:242`), routes the 5
  operator-spine groups to `<group>.hub` (~`:248`), and falls through to the
  blocked `group_pending` for the rest (~`:277`) — the oracle (`f87fa508`)
  opens the per-group edit page uniformly for all groups.
- **Verify:** `python3 -m pytest -q --ignore=examples` → **3445 passed, 29
  skipped, 1 warning** (docs-only; deps installed into the container this
  session first — pytest was absent). The `examples/` collection path is
  excluded per the standing pre-existing plugin-example import gap.

## Trail

- Two rows MOVED from "GENUINELY OPEN" into "DONE / NOT-A-GAP", mirroring how
  #556 flipped C1: **B2** (evidence #527 `1e61fe6`, panels `:797-811`, golden +
  test) and **B3** (#532 `cae15f8`, selector `:1240-1241` / handler `:1172-1242`,
  golden + test). Each reformatted to the DONE table's 3 columns
  (Item | Verdict | Evidence). No other rows touched.
- **question-router.md:** appended ONE open owner-intent block (`### Q:` +
  the documented field set: Area/Type/Priority/Status, Question, Why, Options,
  Safe default, Maintainer answer pending, Routing result pending) for the
  per-group edit-page group-routing decision; updated the section's
  "(No unanswered blocks)" note to "(One unanswered block below …)" so the
  header stays truthful. No decision-ID (`D-00NN`) token minted (verified by
  grep) — the file's native token is `Q-`, and the concrete answered entries
  carry descriptive `### Q:` titles without own numbers, so I matched that.
- DECIDE-AND-FLAG (PL-001): made the minimal Conclusion consistency touch-up
  the flips force — the Conclusion named B2/B3 as "the remaining mintable
  items" and recommended "closing B2/B3", both of which would contradict the
  table once B2/B3 read DONE. Rewrote those two sentences to "the mintable
  re-points are now closed" / "mintable mining lane now cleared". Same
  precedent #556 set for its own C1/doc-fix flip. No rows or verdicts beyond
  B2/B3 changed.

## 💡 Session idea

#556's report *claimed* it routed the group_pending decision to
`docs/question-router.md`, but the block never landed — a report-vs-artifact
drift this session had to catch by grepping the target file rather than
trusting the prior card. A cheap standing guard would close that gap: when a
session card or PR body asserts "routed to `<doc>`" (or "appended to", "recorded
in"), the `check` gate could require the SAME PR's diff to actually touch that
named doc — flagging "claimed-but-unlanded" routing mechanically. It would not
judge whether the routed content is correct, only that the artifact the report
promised actually exists in the diff — the precise failure that left this
decision unrouted for a full reconcile cycle.

## ⟲ Previous-session review

The 2026-07-18 reconcile-completeness-table-c1 session (`complete`, #556) did
disciplined verify-first work flipping C1 + the wizard doc-fix and re-scoping
group_pending as an epic — but it left two adjacent mining rows (B2/B3) stale
and its report claimed a question-router routing that never landed; a good
reminder that a reconcile is only as complete as its narrowest un-rechecked
row, and that "routed to X" in a report is a claim to verify against X, not a
fact.

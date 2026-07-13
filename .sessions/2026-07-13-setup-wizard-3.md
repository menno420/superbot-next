# 2026-07-13 — setup wizard successors slice 3: the suggestion Edit lane

> **Status:** complete

- **📊 Model:** Fable · setup-wizard successor lane, slice 3

## Scope

Port the oracle per-suggestion **Edit** action (menno420/superbot
`disbot/views/setup/ai_review/per_recommendation.py` — the Q-0048
Accept·Deny·Edit finalize's third control) onto superbot-next's
panel/handler idiom: for a `create` suggestion Edit opens the
"Edit suggestion" rename modal (a G-10 declared form — the
essential-steps modal twin) whose submit rewrites the recommendation's
`target_name` in the shared draft, re-accepts it under the unchanged
binding key, and advances the walkthrough (`apply_edit` /
`_swap_and_accept`, ported); for a `bind` suggestion Edit explains —
oracle copy verbatim — that an existing resource can't be renamed here
and Deny+rebind is the path (the native re-pick picker sub-view stays
a flagged follow-up). The edited state flows through
`review_stage`/final-review: the staged `bind_channel` payload now
carries `target_name`, so the final-review Pending line renders the
(possibly edited) name instead of the raw id. The 10 per-section
flows (`setup.open_section_*`) and the linear wizard steps stay
honest terminals, untouched; golden-pinned OPEN renders stay
byte-identical.

## 💡 Session idea

The Edit face is the third setup panel whose CONTROL SET depends on
per-render state (final-review drops Apply when nothing is staged, the
hub depth-filters its section buttons, now review_item swaps which Edit
button shows by suggestion mode) — and each does it by filtering
`base.components` on hardcoded custom_id strings inside its renderer
override, even though the grammar already HAS a declared
`visible_when` facet with render-time + dispatch-time evaluation
(games panels use it). The facet's EvalContext only reaches
guild-scoped reads (settings/bindings/capabilities/flags), so
per-`guild:user` session state — walkthrough index, staged-count,
flow phase — can't ride it. Extending EvalContext with an optional
session-state read would let all three setup panels declare their
visibility rules as data, and the dispatch-time re-evaluation would
replace every hand-rolled stale-card guard for free.

## ⟲ Previous-session review

Slice 2 (essential steps 2–8, PR #397) landed the exact G-10 modal
pattern this slice copies (`DeferMode.MODAL` + static `ModalSpec` +
the submit handler reading `req.args` — `setup.essential_log_names`),
which made the rename modal a mechanical port. One friction point it
left: its modal forms silently dropped the oracle's dynamic field
defaults (pre-filled current values) without a per-form ledger line —
the static-wire-bytes divergence is only documented at the engine
level (resolve.py's stash comment), so each new form has to rediscover
why its `default=` can't be dynamic.

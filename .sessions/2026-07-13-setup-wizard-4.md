# 2026-07-13 — setup wizard successors slice 4: the section-flow spine + first two flows

> **Status:** in-progress

- **📊 Model:** Fable · setup-wizard successor lane, slice 4

## Scope

Port the section-flow SPINE + the first two per-section flows +
the linear wizard steps from the LOCAL oracle clone
(menno420/superbot): `views/setup/section_card.py` (the shared
render/stage/skip/back frame — the four-button card, the
setup_progress status/badge vocabulary, the
replace-recommended-for-section staging semantics over the K9
draft store), `views/setup/wizard_nav.py` + `views/setup/wizard.py`'s
`LinearWizardView`/`build_wizard_step_embed` (the one-step-at-a-time
wizard behind the hub's ↩ Back to wizard — flips the
`setup.back_to_wizard` honest terminal), and the first two section
flows: `sections/preset_select.py` (the 7-preset catalogue verbatim,
pick → preview → stage-every-op into the K9 draft) and
`sections/channels.py` (the declared-CHANNEL-binding walk, the
binding picker → native channel picker → staged `bind_channel`,
plus the high-confidence Apply-Recommended builder) — flipping
`setup.open_section_preset_select` and `setup.open_section_channels`.
The other SEVEN section slugs stay honest named-successor
terminals. Copy/labels/flow verbatim; the adaptation idiom is the
final_review.py / essential_steps.py / wizard.py Edit-lane doctrine
(open_panel navigation, renderer overrides composing the embed,
flow state per guild:user in memory, K7/K9 seams for every write).

## 💡 Session idea

The K9 `DraftOperation.label` is now doing triple duty as the
section-provenance carrier (`[suggestions] `, `[recommended:<slug>] `,
`[<slug>] ` prefixes) — the oracle carried `section_slug` +
`staging_kind` as typed COLUMNS (migration 035) with cosmetic labels
on top. If a third consumer of provenance appears (e.g. the
per-section pending breakdown on the hub), consider widening
`sb_draft_operations` with the two typed columns instead of growing
the label micro-grammar — parse-from-label is one rename away from a
silent provenance loss.

## Review remark — previous session (slice 3, the Edit lane)

Clean slice: the two-Edit-faces panel trick (declare both controls,
renderer keeps one per mode) is exactly the right grammar-side answer
to the oracle's dynamic button, and pre-registering `target_name` on
the staged payload saved this slice from a schema dance. One nit: the
bind-face refusal handler re-renders on a stale create-face card but
the rename-modal submit path answers the bind refusal without a
re-render — the stale card stays up; harmless (next click heals) but
asymmetric.

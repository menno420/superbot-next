# 2026-07-13 — setup wizard successors slice 2: essential steps 2–8

> **Status:** in-progress

- **📊 Model:** Fable · setup-wizard successor lane, slice 2

## Scope

Port the oracle Essential Setup spine's steps 2–8 (menno420/superbot
`disbot/views/setup/essential_setup.py` — GreetMembersStep,
ModeratorsStep, BlockSpamStep, LogChannelStep, RewardActivityStep,
HelpDeskStep, CommandChannelsStep), the closing EssentialSummaryView
(+ extras menu + Check-my-setup health read), and the restart-resume
lane (EssentialSetupResumeView + the persisted `essential_step`
anchor) onto superbot-next's panel/handler idiom: each step's card
renders verbatim copy, Save & continue applies IMMEDIATELY through the
audited kernel seams (K7 `settings.set_scalar` / `settings.bind` /
`ticket.update_config` / `role.set_threshold` /
`platform.set_access_mode(+channels)`; channel/role creation through
the armed state-action ports with the audit companions), Skip records
and advances, and Step-1's Save/Skip confirmation stops naming this
slice as a successor and actually advances into Step 2. The 10
per-section flows and the suggestion Edit lane keep their honest
terminals untouched; golden-pinned OPEN renders stay byte-identical.

## 💡 Session idea

Every stateful step panel here re-implements the same triple —
in-memory per-`guild:user` flow state + a renderer override that
re-reads it + `refresh_session_view` after every pick. A kernel-lane
`StatefulPanelSpec` facet (declared state schema, engine-owned
store/refresh, state handed to the renderer ctx) would collapse the
wizard's ~20 pick handlers into declarations and give EVERY future
multi-select surface (ticket setup's pending dict, the section flows
to come) the same restart semantics for free.

## ⟲ Previous-session review

Slice 1 (final-review apply lane, PR #395) left exactly the seams it
promised: the dynamic `wizard.can_apply_setup` module-attribute gate
read, `wizard._write_setting`, and the renderer-override
component-filter pattern (`_render_final_review` dropping the Apply
button) which this slice reuses for every phase/mode-dependent
control. One friction point: its layout-lock exemption prose is
duplicated byte-identical across three keys per panel — this slice
has five above-floor panels, so that convention costs ~15 identical
paragraphs; a shared `provenance_ref` would be cheaper.

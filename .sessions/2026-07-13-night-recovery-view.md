# 2026-07-13 — SectionRecoveryView + workspace-notice ride (ORDER 019 item 5b, night lane)

> **Status:** `complete`

- **📊 Model:** `Fable (Claude 5 family)` · NIGHT-RUN port slice · mandate:
  ORDER 019 item 5(b) — the SectionRecoveryView + workspace-notice ride,
  a surviving setup-wizard follow-up per
  `docs/status/completeness-table-2026-07-13.md` setup row. Claimed in
  `control/claims/night-setup-followups-windowed-select.md` (claim PR #431).

## Scope

Port the oracle's section-recovery surface (re-entry when a setup section
flow errors out) and the workspace-notice ride (one-shot durable event
records in the workspace channel) into `sb/domain/setup`, faithful at the
seam level, idiomatic to the target grammar (PanelSpec, audited K7 ops),
riding the panel lanes #437 (resume sweep + boot-hook seam) just landed.

## Close-out

Landed as PR #444 (implementation commit 3495c94). What the oracle pair
turned out to be (menno420/superbot @bbc524e4): `views/setup/recovery.py`
is Phase 7 of the setup-wizard plan — when a section's Apply-Recommended
path raises, `LinearWizardView._mount_recovery_view` swaps the anchor to
a structured gold embed (What happened / Why / Recommended / If skipped,
the permission-hint ladder for Forbidden/HTTPException/TimeoutError) with
Continue · Retry · Skip section · Customize · Cancel, the mutating
buttons re-gated per click; `views/setup/_anchor.py push_setup_notice` is
the anchor-split's event half — append a one-shot durable notice into the
workspace channel, NEVER touching the anchor message id, never raising
(bool contract), ridden by Apply Recommended ("✅ Recommended staged"),
Apply-all, the hub's section-failure record and `/setup-status`.

Ported: `sb/domain/setup/recovery.py` — the `setup.section_recovery`
panel (oracle labels/styles/rows/`setup_recovery:*` custom_ids verbatim),
`RecoveryContext` per guild:user (the wizard_nav step-index precedent for
the oracle's view-instance state), `recovery_context_from_exception`
(copy + hint ladder verbatim), Continue/Skip repaint the host through the
`open_panel` seam (origin-tagged wizard/hub), Retry/Customize re-enter
the section via its registered `setup.open_section_{slug}` route (the
`section.run` twin) or its detail panel, Skip writes through the K7
`setup.set_section_skip` lane + the provenance delete;
`sb/domain/setup/notices.py` — `push_setup_notice` over
`service.post_panel_to_channel` + the component-less
`setup.workspace_notice` panel (the status-card precedent);
`wizard_nav.py` — the two Apply-Recommended failure catches now mount
the recovery panel, Apply Recommended + Apply-all post the shipped
notice embeds (bytes verbatim). Manifest: both panels declared;
layout-lock Exempt pins for the 5-action recovery panel (oracle rows
cited); snapshot + sim-gate baseline + compat pin (`setup_recovery:*`)
regenerated through their sanctioned `--write` paths.

Evidence: `python3 -m pytest tests/ -q` **2953 passed, 15 skipped**
(23 new in `tests/unit/setup_band/test_section_recovery.py`, DB-free per
the wizard-interior convention); shadowing/namespace/no-skip/config +
sim-gate + compat + `manifest_compile` all green. `bootstrap.py check
--strict` carries two findings that PRE-EXIST on origin/main (verified
on a pristine origin/main probe worktree: the #440 fleet-cleanup audit's
[reachable] orphan + [stamp] D-0046 double-cite) — not this slice's,
left for the docs lane.

Decisions flagged: Apply Recommended keeps the text reply as the
click-level ack ALONGSIDE the durable notice (the oracle answered with a
bare defer; the reply seam keeps the confirmation visible when the
workspace is unreachable — ledgered in the wizard_nav docstring);
`RecoveryContext.if_skipped` always takes the oracle's generic
fall-through (the target `WizardSectionSpec` carries no
`description_if_skipped`). Deferral: the oracle hub's section-failure
notice ("⚠️ Section `slug` failed") — the target's hub buttons dispatch
straight to per-section handlers with no shared catch seam; wiring it
means either a router-level notice hook or per-section wraps, a small
own slice.

## 💡 Session idea

`push_setup_notice` is setup-shaped only by its channel resolver — the
"durable event record next to an anchored panel" pattern is exactly what
the final-review apply lane and the resume sweep's error paths want too.
A kernel-band `post_notice(channel_ref, embed_params)` twin of
`edit_anchored_panel` (the same presenter port, channel-send branch)
would let every domain post never-raising event records without minting
a per-domain notice panel; recipe: lift `notices.push_setup_notice`'s
body into `sb/kernel/panels/engine.py` beside `edit_anchored_panel`,
keep the domain panel as the embed composer, pin with a
test_edit_anchored.py-style unit that a dead channel answers False.

## ⟲ Previous-session review

The night-onready-resume session (PR #437) closed its lane exactly as
carded — the boot-hook seam, the `edit_anchored_panel` editor port and
the two-leg sweep all landed layer-legal with the counters test-pinned,
and its card's seam inventory made this slice's research trivial (the
panel/notice lane split it named is precisely where this port attached).
Its completeness true-up discipline held (row flipped in the same PR);
the one gap worth naming: its strict-check "green minus this card's own
born-red hold" claim predates the #440 audit findings now sitting red on
origin/main — the next docs lane should link/badge that audit before the
strict check reads honest again.

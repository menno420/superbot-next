# 2026-07-13 — setup wizard successors slice 5: the settings-write section flows

> **Status:** in-progress

- **📊 Model:** Fable · setup-wizard successor lane, slice 5

## Scope

Port the three SETTINGS-WRITE section flows from the LOCAL oracle
clone (menno420/superbot) onto the slice-4 spine
(`sb/domain/setup/section_card.py` + `wizard_nav.py`):
`views/setup/sections/logging_presets.py` (the Single / Balanced /
Detailed / Custom picker over the 8-binding logging catalogue —
every preset stages `create_channel` rows only; Apply Recommended =
Balanced), `views/setup/sections/moderation.py` (the four-knob
detail view — DM-on-action, require-a-reason, warn escalation,
moderator role — each pick staging a `set_setting` row through the
registered `settings.set_scalar` op kind; Apply Recommended = DM +
reason), and `views/setup/sections/cleanup.py` (the scope walker —
guild default / category override / channel override × Off / Light /
Standard / Strict — plus the six-profile batch picker, each pick
staging `set_cleanup_policy`, newly registered onto the audited K7
`governance.set_cleanup` op). Flips `setup.open_section_
logging_presets` / `_moderation` / `_cleanup` into `wizard.py`'s
`_LIVE_SECTIONS`; `roles` · `role_templates` · `cog_routing` ·
`ticket` stay honest terminals. Copy/labels/flow verbatim; the
adaptation idiom is the slice-4 preset_select.py / channels.py
doctrine (renderer overrides composing the embed, flow state per
guild:user, provenance-labelled K9 rows, K7 seams for every write).

## 💡 Session idea

Three sections now translate an operator-facing LEVEL vocabulary
into column payloads at STAGE time (cleanup's Off/Light/Standard/
Strict → the three cleanup_policies columns). If the level table
ever drifts from the staged rows (a re-tuned `Light`), already-staged
drafts silently apply the OLD columns — consider stamping the level
name into the payload (done here as `level`) AND having the apply
leg re-derive columns from the level when present, so a draft staged
last week applies this week's meaning of `Light`.

## ⟲ Previous-session review

(slice 4, the spine)

The spine's plug-point design paid off exactly as advertised — this
slice registered three flows without touching section_card.py at
all. Two observations: (1) `stage_custom`'s slot key
`(op_kind, subsystem, payload["name"])` quietly requires every
staged payload to carry a `name` — cleanup's scope rows had to mint
a synthetic `name` to get per-scope replace-on-conflict; worth a
docstring note on StagedSectionOp. (2) final_review's `_short_label`
ignores the stored K9 label (which carries provenance prefixes), so
any new op kind needs its own label branch there — a small hidden
coupling between staging modules and the review renderer.

# 2026-07-19 — settings epic S4: the free-text modal edit widget

> **Status:** `complete`

- **📊 Model:** opus · high · feature build

## Scope

Execute **slice S4** of the settings `group_pending` epic
(`docs/design/settings-group-pending-epic-plan.md`): port the oracle
free-text edit modal (`disbot/views/settings/edit_text.py` +
`subsystem_view.dispatch_edit_setting` free-form-string arm @ `menno420/superbot
f87fa508`) onto the shipped `settings.group_edit` page frame (S0, PR #579;
S2 enum, PR #580; S3 number, PR #581). Picking a `str`-without-`allowed_values`
scalar in the Edit select opens a session-view child
(`settings.group_edit_text`) whose button ISSUES a G-10 `ModalSpec`
free-text-input modal; the submit validates (non-empty + declared `bounds`
max-length per the SettingSpec) and commits the entered string through the
existing `settings.set_scalar` K7 op — no new op minted.

Stacked on S3 (#581): the text branch was cut from the pre-merge S3 branch;
S3 squash-merged into `main` before the first push, so the branch was rebased
`--onto origin/main` and the PR base is `main` with a clean text-only diff.

Deliverables:
- The `settings.group_edit_text` widget panel: a session-view child whose
  single button issues the ported `TextSettingModal` (a one-input free-text
  modal), opened from the `settings.group_edit` Edit select when the picked
  spec is free-text-shaped (`value_type == str` AND no `allowed_values`). The
  submit rejects an empty value and a value over the declared `bounds`
  max-length (`(max_len,)` for str), and commits through `settings.set_scalar`
  (the ADMIN-floor K7 scalar lane); a rejected entry writes nothing. The
  (group, setting) ride the kernel modal-args stash restored at submit (the S3
  `group_edit_number_submit` precedent). The widget refreshes in place.
- The bool toggle (S1) + enum select (S2) + number modal (S3) stay live; reset
  keeps clearing text settings through `settings.clear_scalar` (the S0 reset
  select is type-agnostic).
- Preserve the option-A boundary: the 5 operator-spine hub arms + the `games`
  panel arm untouched.
- Compat-frozen §5.3 pin amended for the new `settings.group_edit_text_form`
  modal custom_id (via `tools/check_compat_frozen.py --write`).
- Unit tests: a text setting opens the modal widget; a valid submit persists
  the scalar via `set_scalar`; an empty / over-length submit is rejected
  without a write (with the error copy); reset clears a text setting.
- Golden: `parity/goldens/settings/group_edit_text_write.json`, minted
  honestly via the oracle-replay path.

## Result

Landed the S4 free-text-modal edit widget on PR #582. Picking a
`str`-without-`allowed_values` scalar in the `settings.group_edit` Edit select
now opens the free-text-modal widget `settings.group_edit_text`
(`sb/domain/settings/panels.py` `settings_group_edit_text_spec` +
`_group_edit_text_fields` provider; the new `_is_text_spec` predicate + the
`_TEXT_MODAL` G-10 `ModalSpec`, a paragraph/multi-line input), whose
"Enter text…" button ISSUES the free-text modal. On submit, the typed string is
validated (non-empty + the declared `bounds` max-length `(max_len,)` per the
`SettingSpec`) and commits through the existing K7 `settings.set_scalar` lane
(`sb/domain/settings/handlers.py` `group_edit_pick` text branch +
`group_edit_text_submit` / `group_edit_text_back` handlers + the
`_refresh_group_edit_text` in-place refresh) — no new op minted. An empty /
over-length entry rejects without a write. The (group, setting) ride the kernel
modal-args stash restored at submit (the S3 `group_edit_number_submit`
precedent) — no parallel session dict.

Faithful to the oracle `dispatch_edit_setting` order, `_is_text_spec` EXCLUDES
the `channel`/`role`/`numeric_presets` `input_hint`s (the S5–S7 widget targets
the oracle routes BEFORE the free-text fallback). Flagged finding: after S4,
every editable scalar in the current corpus routes to a live widget
(bool/enum/number/free-text) — no editable setting is list-typed or carries a
pointer `input_hint` today, so the "ports in a later slice (S5–S7)" placeholder
is now defensive-only for real settings; the `test_non_bool_pick_degrades`
regression test was repointed onto a synthetic `input_hint="channel"` spec to
keep exercising that honest-degrade arm.

Bool (S1) + enum (S2) + number (S3) stay live; text reset keeps clearing
through `settings.clear_scalar` (the S0 reset select is type-agnostic).
Option-A boundary preserved (the 5 hub arms + `games` untouched). Manifest
snapshot recompiled (49 manifests). Golden
`settings_group_edit_text_write.json` minted honestly via the oracle-replay
path (`karma.reaction_emoji` str, bounds `(64,)` → `⭐`; the `settings` db_delta
writes `karma_reaction_emoji=⭐`; step-4 issues the type-2 button, step-5 submits
the type-9 modal + commits). Golden corpus 530 → 531 (minted 68 → 69);
count-pins resynced in `test_check_parity_depth.py` + `test_replay_adapter.py`.
Compat-frozen §5.3 pin amended for the new `settings.group_edit_text_form`
modal custom_id (via `tools/check_compat_frozen.py --write`).
Full `python3 -m pytest tests/unit` — **3523 passed, 15 skipped**;
`check_symbol_shadowing` / `namespace` / `no_skip` / `config_usage` /
`check_orphan_pendings` clean; `check_compat_frozen` green. The full
`--ignore=examples` corpus + golden-parity replay is left to CI's authoritative
gates on the PR (a local full run under a single Postgres deadlocks against the
parity gate — S3's confirmed env-only note).

## 💡 Session idea

S4 confirmed the S3 idea's prediction — the modal-widget playbook line
("child session-view + issuing button; selection rides the modal-args STASH;
golden needs BOTH the issue click and the submit step") ported to a string
field verbatim, zero new machinery. The genuinely NEW lesson is the *dispatch
frontier*: S4 is the last value-type arm, so the free-text predicate must be
the DISPATCH-ORDER COMPLEMENT of the arms above it AND the pointer arms below
it — `str AND not allowed_values AND input_hint not in {channel,role,presets}`.
The oracle encoded that ordering imperatively (input_hint checked first, then
value_type fallback); a declarative per-arm predicate set only stays disjoint if
each new arm subtracts BOTH directions. Worth pinning as the widget-frontier
rule: "a value-type dispatch arm's predicate must exclude every sibling arm's
claim in BOTH directions — the ones already landed and the ones the oracle
routes ahead of it — or a later slice silently loses its targets." S5/S6 will
lean on this exact exclusion (they claim the input_hints S4 just carved out).

## ⟲ Previous-session review

S3 (number) left the frame in exactly the shape S4 needed: the `_is_*_spec`
predicate + child-session-view-with-baked-args + modal-args-stash pattern
generalized to `_is_text_spec` with zero churn to the shared `group_edit_pick`
/ reset / refresh seams, and S3's own comment already anticipated
`role.skip_roles` as "str — S4 text widget", so the one regression it planted
was self-documenting. The only thing S3 could not foresee: that S4 would close
the value-type frontier and turn the S5–S7 placeholder into defensive-only code
— a fact worth carrying into S5's plan note.

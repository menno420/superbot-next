# settings `group_pending` — per-group scalar-edit-page epic plan

> **Status:** `plan`
>
> A forward implementation **plan** for the settings-mutation epic — the
> ported per-group scalar-EDIT page that replaces the honest `group_pending`
> terminal. This is a PLAN, not built code: it makes the epic executable as a
> chain of clean slices. The code and `docs/decisions.md` win once slices land.
> Evidence citations are `file:line` at HEAD `6b84248` unless noted; oracle
> citations are `menno420/superbot @ f87fa508`. (The docs-gate badge taxonomy
> has no `epic`/`proposal` token — `bootstrap.py:270-282` — so the design-series
> `plan` badge carries it, per the D2/D3/D4 precedent.)

## TL;DR

The oracle's Settings hub opens a per-group **`SubsystemSettingsView`**
type-specific scalar EDIT page for every group; the port instead routes 5
operator-spine groups to their read-only `<group>.hub`, one group (`games`) to
its dedicated panel, and every other group to the blocked
`settings.group_pending` terminal. The **owner has ruled option A**
(`docs/question-router.md` → Answered, 2026-07-18): the ported edit page
replaces `group_pending` for the **non-hub groups only**; the 5 operator-spine
hub groups keep their existing hubs. This doc scopes that build as **S0** (the
page frame) followed by **S1–S7** (one slice per edit widget), each landing onto
seams that **already exist** (the K7 `set_scalar` / `clear_scalar` write ops,
the `MODAL` defer adapter, the windowed-select helper) with its own
oracle-replay golden.

## Owner decision (scope gate)

**Option A — edit page for the NON-HUB groups only.** Provenance:
coordinator-relayed owner directive, 2026-07-18 ~21:20Z; recorded
decide-and-flag (PL-001, silence = consent). Routed from
[../question-router.md](../question-router.md) (Answered section).

Concretely, the per-group open (`settings.open_group`,
`sb/domain/settings/handlers.py:249`) keeps its three-way branch and the edit
page is wired **only into the third arm**:

| Group class | Members | Open target | This epic |
|---|---|---|---|
| Operator-spine hubs | `welcome`, `counters`, `security`, `automod`, `image_moderation` (`ensure_hub(...)` in `sb/manifest/<group>.py`; gate `has_operator_hub`, `handlers.py:272`) | `<group>.hub` (read-only) | **unchanged** |
| Dedicated panel | `games` → `games.sections` (`_GROUP_PANELS`, `handlers.py:37`, `:269`) | `open_panel(games.sections)` | **unchanged** |
| Everything else | every other declared settings group | `group_pending` BLOCKED terminal (`handlers.py:242` registration, `:277` fallthrough) | **replaced by the ported edit page** |

Only the third arm changes: the `BLOCKED` return at `handlers.py:277`
(and the retired-explorer-style `group_pending` registration at `:242`) is
displaced by an `open_panel(settings.group_edit)` route once S0 lands. The
first two arms (`:269` `_GROUP_PANELS`, `:272` `has_operator_hub`) are never
touched — that is the whole content of option A.

## Existing seams to build ONTO (do not reinvent)

The cost of this epic is **breadth, not a missing seam** — the write path and
the panel machinery already exist:

- **Write ops (K7 compound ops).** `settings.set_scalar` and
  `settings.clear_scalar` — `sb/domain/settings/ops.py` `SET_SCALAR` (`:264`,
  leg `settings.write_scalar`, `audit_verb="setting_set"`) and `CLEAR_SCALAR`
  (`:277`, leg `settings.erase_scalar`, `audit_verb="setting_cleared"`), both
  `WorkflowLane.SCALAR`, `reversible`, ADMIN floor. Every widget's commit and
  every reset lands on these two ops — no new op is minted by this epic.
- **Modal adapter.** `ModalSpec` / `ModalFieldSpec` (`sb/spec/panels.py:243`,
  `:258`) plus the `defer_mode == MODAL` component invariant
  (`panels.py:310`, G-10: `defer_mode==MODAL ⇒ modal is not None`). The
  number-modal (S3) and free-text-modal (S4) widgets declare a `ModalSpec` and
  submit back through the frozen MODAL adapter → `resolve()`.
- **Windowed selects.** `sb/kernel/panels/selectwindow.py` (the ≤25-option
  paginated select helper) backs the Edit-a-setting and Reset selects on the
  page frame (S0) and the enum (S2), channel (S5), and role (S6) widgets whose
  option sets can exceed the Discord 25-option ceiling.
- **Pattern reference — the one already-ported widget.** The oracle's
  `edit_command_access.py` (~505 lines) is already ported: its command-access
  editor lives in `sb/domain/settings/handlers.py` (`:412+`, wiring onto
  `sb/domain/platform/command_access.py` `set_access_mode` / `set_access_channels`)
  with per-message session state in `_ACCESS_SESSIONS` (`handlers.py:47`). Use
  it as the concrete template for: per-message session state keyed by panel
  message id, the mode-button → K7-value dispatch table, the `refresh` re-render
  pattern, and the polite text-degrade on an expired session.

## Slice breakdown

Each slice is its own PR with its own oracle-replay golden and lands green
before the next opens. Ordering: **S0 first** (the page frame, dispatching
edit/reset to at least one live widget), then S1–S7 add widgets incrementally.

### S0 — the page frame (`settings.group_edit`)

- **Delivers:** the per-group edit page itself — a dynamic READ embed of the
  group's current scalar values, a windowed **"Edit a setting…"** select, a
  windowed **"Reset a setting…"** select, and **Back-to-Hub** / **Open-Panel**
  navigation buttons; per-message session state (selected group + running
  selection) keyed by the panel message id. The `settings.open_group` third arm
  (`handlers.py:277`) is re-pointed from `group_pending` BLOCKED to
  `open_panel(settings.group_edit)` for non-hub groups; `group_pending`
  (`:242`) is retired the way slices 1–3 retired the read-only diagnostics'
  pending refs.
- **Ports:** the oracle `SubsystemSettingsView` frame
  (`disbot/views/settings/subsystem_view.py` @ f87fa508) — the read embed +
  the edit/reset selectors + nav, minus the per-type widget bodies (those are
  S1–S7).
- **Seam:** the two selects ride `selectwindow.py`; edit-commit and reset
  dispatch onto `settings.set_scalar` / `settings.clear_scalar` (`ops.py:264` /
  `:277`); session state mirrors `_ACCESS_SESSIONS` (`handlers.py:47`).
- **Golden / test:** `parity/goldens/settings/group_edit_open.json` (the page
  open render) + a write golden for the first wired widget; a unit test that the
  non-hub `open_group` arm now opens `settings.group_edit` and the 5 hub arms +
  `games` are unchanged (assert `has_operator_hub` / `_GROUP_PANELS` branches
  still route as before). **S0 must land the page frame wired to at least one
  widget** (S1 bool is the natural first) so the slice is exercisable
  end-to-end, not a dead frame.

### S1 — bool toggle

- **Delivers:** a two-state toggle button for boolean scalars (on/off).
- **Ports:** the oracle bool-edit widget of `SubsystemSettingsView`.
- **Seam:** click → `settings.set_scalar` with the flipped value; re-render via
  the S0 refresh.
- **Golden / test:** `parity/goldens/settings/group_edit_bool_write.json` +
  a unit test asserting the toggle emits `set_scalar` with the inverted bool.

### S2 — enum select

- **Delivers:** a select of the allowed enum choices for an enum-typed scalar.
- **Ports:** the oracle enum-edit widget.
- **Seam:** windowed select (`selectwindow.py`) → `settings.set_scalar` with
  the chosen member.
- **Golden / test:** `parity/goldens/settings/group_edit_enum_write.json` +
  a test that an out-of-window option page still resolves to the right value.

### S3 — number modal

- **Delivers:** a modal capturing a numeric value (with range/validation copy).
- **Ports:** the oracle number-edit modal.
- **Seam:** `ModalSpec` + `defer_mode == MODAL` (`panels.py:243/258/310`);
  submit → `settings.set_scalar` after parse/validate.
- **Golden / test:** `parity/goldens/settings/group_edit_number_write.json` +
  a test covering a reject (non-numeric / out-of-range → no write, error copy).

### S4 — free-text modal

- **Delivers:** a modal capturing a free-text scalar (length-bounded).
- **Ports:** the oracle text-edit modal.
- **Seam:** `ModalSpec` / `ModalFieldSpec`; submit → `settings.set_scalar`.
- **Golden / test:** `parity/goldens/settings/group_edit_text_write.json` +
  a length-bound reject test.

### S5 — channel select

- **Delivers:** a channel picker for channel-pointer scalars.
- **Ports:** the oracle channel-edit widget.
- **Seam:** windowed channel select (`selectwindow.py`) → `settings.set_scalar`
  (channel id). (Where a scalar is genuinely a binding pointer rather than a KV
  scalar, flag it in the slice PR — bindings have their own route-truth; keep
  this widget to scalar channel keys.)
- **Golden / test:** `parity/goldens/settings/group_edit_channel_write.json`.

### S6 — role select

- **Delivers:** a role picker for role-pointer scalars.
- **Ports:** the oracle role-edit widget.
- **Seam:** windowed role select (`selectwindow.py`) → `settings.set_scalar`.
- **Golden / test:** `parity/goldens/settings/group_edit_role_write.json`.

### S7 — numeric-presets buttons

- **Delivers:** a row of quick-set preset buttons for a numeric scalar
  (e.g. common thresholds), complementing the S3 modal for arbitrary values.
- **Ports:** the oracle numeric-presets widget.
- **Seam:** each preset button → `settings.set_scalar` with its fixed value.
- **Golden / test:** `parity/goldens/settings/group_edit_presets_write.json`.

## Risks / notes

- **One golden per widget.** Each slice ships its own oracle-replay golden;
  parity is replayed against the local oracle (`f87fa508`) per slice. No image
  bytes are involved here (these surfaces are embeds + modals + components, not
  rendered cards), so the "bytes not asserted where images involved" carve-out
  is **n/a** — assert the full render.
- **No single group is pure-bool.** Real groups mix value types, so S0's read
  embed and its edit/reset dispatch must handle multiple scalar types the
  moment ≥2 widgets have landed — the frame cannot assume a single widget kind.
  Land S0 wired to S1 (bool), then keep the frame type-dispatching as S2–S7
  extend the widget set.
- **Option-A boundary is load-bearing.** The 5 hub arms (`handlers.py:272`) and
  the `games` panel arm (`:269`) must stay untouched by every slice; a slice
  that widens the edit page to a hub group would silently re-home a shipped hub
  route and contradict the owner ruling. S0's unit test pins this boundary.
- **`group_pending` retirement is one-way per group.** Once S0 re-points the
  non-hub arm, the honest blocked terminal no longer stands for those groups —
  so S0 must ship the read embed + at least one working widget, not a
  half-wired page that reads worse than the honest block it replaced.
- **Record the decision on first landing.** When S0 lands, add the
  `docs/decisions.md` entry citing the question-router Answered block (the
  routing result promised there), closing the plan→decision loop.

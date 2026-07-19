# 2026-07-19 — settings epic S5: the channel-select edit widget

> **Status:** `complete`

- **📊 Model:** opus · high · feature build

## Scope

Execute **slice S5** of the settings `group_pending` epic
(`docs/design/settings-group-pending-epic-plan.md`): port the oracle
channel-select edit widget (`disbot/views/settings/edit_channel.py` + the
`channel` arm of `subsystem_view.dispatch_edit_setting` @ `menno420/superbot
f87fa508`) onto the shipped `settings.group_edit` page frame (S0, PR #579; S2
enum, PR #580; S3 number, PR #581; S4 text, PR #582). Picking a
`channel`-hinted scalar (`input_hint="channel"`) in the Edit select opens a
session-view child (`settings.group_edit_channel`) whose windowed component
select lists the guild's channels (fed by the channel-directory read seam,
paged past the 25-option ceiling via `selectwindow.py`); a pick commits the
chosen channel id through the existing `settings.set_scalar` K7 op — no new op
minted.

The `group_edit_pick` dispatch currently routes purely by `value_type` and
IGNORES `input_hint`, so channel settings (`int` + `input_hint="channel"`)
misroute to the S3 number modal. S5 intercepts `input_hint == "channel"`
BEFORE the `_is_number_spec` check (the oracle checks `input_hint` first), so
those settings open the channel picker instead.

Deliverables:
- The `settings.group_edit_channel` widget panel: a session-view child hosting
  a windowed ENUM-kind component select whose options are the guild's channels
  (via `sb.domain.channel.service.active_directory().list_channels`), the
  current channel pre-marked, opened from the `settings.group_edit` Edit select
  when the picked spec is channel-hinted. A pick commits the channel id through
  `settings.set_scalar` (the ADMIN-floor K7 scalar lane); the picker refreshes
  in place. A Back button re-opens the group's edit page. Reset stays on the
  type-agnostic S0 reset select (`settings.clear_scalar`).
- Bool (S1) + enum (S2) + number (S3) + free-text (S4) paths stay live.
- Preserve the option-A boundary: the 5 operator-spine hub arms + the `games`
  panel arm untouched.
- Unit tests: a channel-hinted setting opens the channel picker (NOT the number
  modal — a pinned regression); a pick persists the channel id via
  `set_scalar`; reset clears it; windowed paging works for a many-channel
  guild.
- Golden: `parity/goldens/settings/settings_group_edit_channel_write.json`,
  minted honestly via the oracle-replay path against
  `btd6.strategy_submission_channel`.

## Result

Landed the S5 channel-select edit widget on PR #583. The `group_edit_pick`
dispatch now intercepts `input_hint == "channel"` BEFORE the value_type arms
(the oracle checks input_hint first), so picking a channel-hinted scalar in the
`settings.group_edit` Edit select opens the channel-picker widget
`settings.group_edit_channel` (`sb/domain/settings/panels.py`
`settings_group_edit_channel_spec` + `_group_edit_channel_fields` /
`_group_edit_channel_options` providers; the new `_is_channel_spec` predicate;
`sb/domain/settings/handlers.py` `group_edit_pick` channel branch +
`group_edit_channel_pick` / `group_edit_channel_back` handlers + the
`_refresh_group_edit_channel` in-place refresh). The picker is a windowed
provider-fed ENUM select over the channel-directory roster
(`sb.domain.channel.service.active_directory().list_channels`), paged past
Discord's 25-option ceiling via `selectwindow.py`; a pick commits the chosen
channel id through the existing K7 `settings.set_scalar` lane — no new op — and
refreshes in place. A non-numeric selection rejects without a write.

**Regression fixed + pinned:** `btd6.strategy_submission_channel` (and
`ai.review_channel`) are `int` + `input_hint="channel"`; the value_type-only
dispatch misrouted them to the S3 number modal. The channel arm now intercepts
the hint first, so they open the channel picker
(`test_channel_pick_opens_the_picker_not_the_number_modal` pins this against the
real btd6 setting).

**Port deviation (flagged):** the oracle used a native `discord.ui.ChannelSelect`
+ a Clear button; the port renders a provider-fed windowed ENUM select over the
channel-directory roster (the port-frame convention — provider options + the
`selectwindow.py` pager, which a native picker cannot window; the channel-cog
`_channel_options` precedent) and relies on the shared type-agnostic S0 reset
select for clearing (the S2 enum posture), not a per-widget Clear button.

**Harness idiom added:** channel-select goldens can name a channel by
`__CHANNEL_<NAME>__` in a click Step's `values` (the command-content
substitution's twin) — the runner rewrites it to the boot-allocated raw channel
id, the capture normalizer redacts it back to `<#name>` in the golden bytes.
Added to BOTH runners (`parity/harness/runner.py` +
`sb/adapters/parity/runner.py`) since they are hand-kept mirrors.

Bool (S1) + enum (S2) + number (S3) + free-text (S4) stay live; channel reset
clears through `settings.clear_scalar` (the S0 reset select is type-agnostic).
Option-A boundary preserved (the 5 hub arms + `games` untouched). Manifest
snapshot recompiled. Golden
`parity/goldens/settings/settings_group_edit_channel_write.json` minted honestly
via the oracle-replay path against `btd6.strategy_submission_channel` (pick
`#general` → the `settings` db_delta writes `btd6_strategy_submission_channel =
<#general>`; the channel picker renders the 4 guild channels). Golden corpus
531 → 532 (minted 69 → 70); count-pins resynced in `test_check_parity_depth.py`
+ `test_replay_adapter.py`. `check_compat_frozen` GREEN with NO drift — a
windowed component select adds component custom_ids but no ModalSpec custom_id,
so the frozen §5.3 contract is untouched (the defensive S2.5 prediction held).
Full `python3 -m pytest tests/unit` — **3534 passed, 15 skipped**;
`check_symbol_shadowing` / `namespace` / `no_skip` / `config_usage` /
`check_orphan_pendings` clean. The full `--ignore=examples` corpus +
golden-parity replay is left to CI's authoritative gates on the PR.

## 💡 Session idea

S5 tested the S4 widget-frontier rule from the other side. S4 predicted the
value-type arms would stay disjoint only if each subtracts BOTH the arms above
AND the pointer arms the oracle routes ahead of the value_type fallback. S5 is
the first of those pointer arms to actually LAND — and it exposed a subtlety the
S4 rule understated: a pointer arm does not subtract from a value_type sibling,
it must PRE-EMPT it in dispatch ORDER, because a channel-hinted `int` genuinely
satisfies `_is_number_spec` too (both predicates return True for
`btd6.strategy_submission_channel`). The disjointness S4 described is a property
of the predicate SET; the correctness here is a property of the dispatch
SEQUENCE. Worth pinning as the pointer-arm rule: "an input_hint arm cannot be
made disjoint from its value_type sibling by predicate alone (a hinted int is
still an int) — it must be ordered BEFORE it, mirroring the oracle's
input_hint-first dispatch. Test the ORDER, not just the predicate" — which is
exactly why `test_channel_pick_opens_the_picker_not_the_number_modal` asserts
the opened panel id, not merely that `_is_channel_spec` is True.

## ⟲ Previous-session review

S4 (free-text modal, #582) left the frame in exactly the shape S5 needed and its
card's flagged finding — that the S5–S7 placeholder had become defensive-only
and the degrade regression was repointed onto a synthetic `input_hint="channel"`
spec — was precisely the breadcrumb that made S5's first move obvious: that
synthetic spec was S5's real target, so the degrade test simply moved one hint
over to `role` (S6) and the channel hint graduated to a live-widget assertion.
The one thing S4 could not foresee: that the channel widget would need a golden
idiom for picking a dynamic channel id (the `__CHANNEL_<NAME>__` value token) —
a harness gap invisible until a windowed channel select had to be replayed.

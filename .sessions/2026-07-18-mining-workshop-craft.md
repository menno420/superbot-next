# Session — mining 🔧 Workshop gear-craft select ported to the oracle (B3) 2026-07-18

> **Status:** `in-progress`
>
> Born red (this card only) as the first commit — holds `substrate-gate` red
> until the deliberate LAST commit flips it `complete` (per `.sessions/README.md`),
> releasing the HOLD so the server-side lander can merge on green. The impl +
> tests + minted golden land in the second commit.

- **📊 Model:** Opus 4 family · high · port

## Goal
Backlog B3: port the mining 🔧 Workshop panel's gear-craft SELECT
(`_CraftSelect`), the workshop panel's last D-0043 pending terminal
(`workshop_craft_pending` at `sb/domain/mining/panels.py`). The dropdown refused
with the honest pending copy ("Crafting gear from the dropdown rides the
deep-system panel port (D-0043) — …"). This slice flips it LIVE: picking a
recipe crafts that gear (materials consume + product + crafting XP in one txn),
faithfully reproducing the oracle `disbot/views/mining/workshop_panel.py`
`_CraftSelect.callback` → `services/mining_workflow.py::craft` → `_rerender` (the
in-place ✅/❌ note re-render).

## Scope
Contained to mining, behind the audited seam. The craft WRITE op already exists
— `mining.craft` → `record_craft` (WP-7, the ported `mining_workflow.craft`),
LIVE and byte-pinned via the `!craft <item>` / `!build <item>` command lane
(`goldens/mining/mining_craft_write.json`). This slice wires the PANEL SELECT
face to that SAME op, mirroring how #527 (B2) wired the skill-spend buttons and
#473 wired the title-equip select to their pre-existing ops. Branch
`claude/mining-workshop-craft` off origin/main `1e61fe6` (#527 merged). Born red
(`in-progress`) as the first commit; flips `complete` as the deliberate LAST
commit.

The diff:
1. **The pick handler** — `sb/domain/mining/panels.py`: new
   `_workshop_craft_pick(req)` (registered in `_register_refs()` as
   `mining.workshop_craft_pick`). Reads the picked recipe off
   `req.args["values"][0]`, runs the `mining.craft` op with `{"item": choice}`,
   then re-renders the panel IN PLACE via `refresh_session_view` with the oracle
   note composition — `("✅ "|"❌ ") + message` as the embed description, SUCCESS
   green / ERROR red frame (degrades to a text reply on a refresh miss). The
   `mining.titles_pick` select precedent verbatim.
2. **The wiring** — `sb/domain/mining/panels.py`: the `ws_craft` selector's
   `on_select` flips from `HandlerRef("mining.workshop_craft_pending")` to
   `mining.workshop_craft_pick`; the `_workshop_button_handlers()`
   pending-registrar (its only entry was the now-ported craft) is retired and
   its `_register_refs()` call removed. `_render_workshop` gains the
   `workshop_note`/`workshop_tone` param paint (the `_render_titles` precedent) —
   byte-neutral on the plain open (note empty → dark_grey, unchanged
   description).
3. **Tests** — `tests/unit/mining/test_mining_workshop_craft.py` (9 cases): the
   spec wires the LIVE pick handler + retires the pending; the pick runs
   `mining.craft` with the picked `item`, paints the ✅ success / ❌ verbatim
   materials-refusal note + green/red frame, degrades to text on a refresh miss;
   the renderer stays dark-grey + note-free on the plain open.
4. **The golden** — `parity/goldens/mining/mining_workshop_craft_write.json`
   (minted per-case via `tools/mint_golden.py mining.workshop_craft_write
   --write`, ORACLE-VERIFIED): `!workshop` then the gear-craft select pick on a
   bronze-2 fixture crafts bronze boots (mining_inventory bronze 2→0 + +1 bronze
   boots + crafting XP) and re-renders IN PLACE with the verbatim
   `✅ Crafted **bronze boots**!` note on the green frame. New curated case in
   `parity/cases/curated.py`; count pins auto-rewritten in `parity/parity.yml` +
   the two count-pin tests (524→525, minted 62→63).
5. **The manifest** — `manifest.snapshot.json` recompiled
   (`tools/manifest_compile.py --write`): the `ws_craft` selector's handler ref
   flips `workshop_craft_pending` → `workshop_craft_pick` (3-line drift).
6. **This card.**

## Trail
- ORACLE (menno420/superbot): `disbot/views/mining/workshop_panel.py`
  `_CraftSelect.callback` (lines 128-136) — the pick calls
  `mining_workflow.craft(user, guild, self.values[0])`, then `_rerender`
  (lines 139-156) rebuilds `build_workshop_embed(note=("✅ "|"❌ ") +
  result.message)` and sets `embed.color = SUCCESS_COLOR|ERROR_COLOR` — the
  in-place panel edit. `services/mining_workflow.py::craft` (lines 336-366) owns
  the recipe/forge/material validation + the verbatim `Crafted **{item}**!` /
  refusal strings.
- SB write already ported: `sb/domain/mining/ops.py::_record_craft` (op
  `mining.craft`, WP-7) is the `mining_workflow.craft` verbatim (advisory-fenced
  `lock_workshop_slot`, recipe resolve + forge gate + material check, then the
  material consume + +1 product + crafting game-XP in one txn). The command lane
  (`build_route`'s argful branch) already drives it and `mining_craft_write.json`
  pins it; the picked recipe rides `ctx.params["item"]` (`_item_from`).
- DELIVERY seam: session selects mint the `ws_craft` component as an ephemeral
  whose stored args carry the panel context (`sb/kernel/panels/engine.py`
  `_mint_ephemeral`:388-391); on pick the chosen value arrives on
  `req.args["values"]` — the same idiom `mining.titles_pick` reads.
- POSTURE (decide-and-flag, sibling-precedent): FAITHFUL in-place re-render (the
  ✅/❌ note + SUCCESS/ERROR frame), NOT the RESULT_CARD divergence the workshop's
  BUTTON lanes (skill_spend WP/B2, forge_build WP-6) accept. Rationale: this is a
  SELECT, and the closest sibling — `mining.titles_pick` (#473), also a mining
  session-panel select whose op re-renders in place — already paved this exact
  road (note/tone params → `renderer_override` → `refresh_session_view` → a
  minted select golden). The oracle `_CraftSelect._rerender` is directly
  reproducible, so reproducing it is strictly more faithful than diverging.
  Flagged for review.
- MINT decision (decide-and-flag): a workshop select pick IS drivable by the SB
  capture harness (`kind="click"` + `component_index` + `values`), proven by the
  landed `mining.title_equip_write` select golden. So this slice MINTS
  `mining.workshop_craft_write`, matching the drivable-select-write sibling. The
  verbatim materials-refusal FAILURE path is UNIT-tested (the in-place refusal
  re-render bytes; the command-lane `mining_craft_no_recipe` already pins the
  op's refusal copy) rather than a second golden — the skill_spend (one write
  golden + unit-tested refusals) posture. mining_inventory already covered by
  mine/sell/craft, so NO exemption retires.
- Compat: `check_compat_frozen` OK — the select is session-minted (no
  `custom_id_override`, no `modal_id`), so `legacy_custom_ids` is untouched → NO
  owner-review blocker. The manifest snapshot recompiles deterministically
  (the 3-line handler-ref rename only).
- Verify: `pytest tests/unit/mining/test_mining_workshop_craft.py` → 9 passed;
  full `tests/unit` → 3329 passed, 2 skipped; parity count-pin suites
  (`parity_adapter` + `parity_gate`) green at 525; `check_parity_depth` → OK (525
  goldens); all four checker scripts clean; `check_compat_frozen` → OK. No
  `golden --gate` run (the CAPABILITIES session-window wall) — per-case
  `mint_golden` ORACLE-VERIFY only; full parity verifies in CI.

## 💡 Session idea
B3 sharpened the B1/B2 "is it already ported?" heuristic with a second axis: the
SURFACE-CLASS lookup isn't just button-vs-modal-vs-command for the mint decision,
it's also the render-POSTURE lookup. The naive move was to clone B2 (skill_spend,
the immediate predecessor) and reply a RESULT_CARD — but B2 is a BUTTON, and
workshop-craft is a SELECT. Grepping `on_select=HandlerRef` for the nearest
select sibling surfaced `mining.titles_pick`, which had already chosen the
in-place `refresh_session_view` posture and built the note/tone renderer plumbing
that made a faithful reproduction cheap. The standing refinement: when porting a
panel face, match the sibling of the SAME COMPONENT KIND (not just the same
subsystem or the most recent PR) — the component kind, not the calendar, predicts
which render posture and which harness-drive shape the corpus already blesses.

## ⟲ Previous-session review
🔎 Prev-session review (`.sessions/2026-07-18-mining-skill-spend.md`, `complete`,
B2): that card's own "Session idea" prescribed exactly the move that carried B3 —
"grep the golden corpus for a sibling that drives the SAME surface class (button
vs modal vs command) before deciding already-ported or unmintable." B3 applied it
and found the extra wrinkle the B2 card couldn't see from a button seat: surface
class also selects the RENDER posture, and the truest sibling for a select is
another select (`titles_pick`), not the most recent button (`skill_spend`). The
prior card also re-confirmed the CAPABILITIES `--gate` session-window wall, so B3
again reached straight for per-case `mint_golden` (dry-run → ORACLE-VERIFY →
`--write`) and left the full corpus to CI. Prior guidance worked as intended and
is now extended one axis further.

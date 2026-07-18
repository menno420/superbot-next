# Session — mining 🌳 Skill Tree per-branch spend buttons ported to the oracle (B2) 2026-07-18

> **Status:** `in-progress`
>
> Born-red first commit (this card only). Holds the PR red via `substrate-gate`
> until the deliberate LAST-commit flip to `complete`, once CI confirms every
> functional gate green.

- **📊 Model:** Opus 4 family · high · port

## Goal
Backlog B2: port the mining 🌳 Skill Tree panel's per-branch SPEND buttons
(⛏️ Mining / ⚔️ Combat / 🍀 Fortune / 🛠️ Crafting), the last skills-panel
D-0043 pending terminal (`skill_spend_pending` at `sb/domain/mining/panels.py`).
Each branch button refused with the honest pending copy ("Spending a skill point
from the panel rides the deep-system panel port — spend now with `!skill
<branch>`"). This slice flips them LIVE: a click spends exactly ONE point into
the clicked branch, faithfully reproducing the oracle
`disbot/views/mining/skills_panel.py` `MiningSkillsView._spend` →
`services/skill_service.py::allocate` (default `n=1`).

## Scope
Contained to mining, behind the audited seam. The skill-spend WRITE op already
exists — `mining.skill` → `record_skill` (WP-5, the ported `allocate`), LIVE and
byte-pinned via the `!skill <branch>` command lane
(`goldens/mining/mining_skill_write.json`). This slice wires the PANEL BUTTON
face to that SAME op, mirroring how #520 wired the vault deposit/withdraw
buttons to the pre-existing stash/unstash op. Branch `claude/mining-skill-spend`
off origin/main `782ca2d` (#524 merged). Born red (`in-progress`) as the first
commit; flips `complete` as the deliberate LAST commit.

The diff:
1. **The route** — `sb/domain/mining/service.py`: new `@handler
   ("mining.skill_spend_route")`. Reads the clicked branch off
   `req.args["session_action"]` (`sk_<branch>` → the branch token), runs the
   `mining.skill` op with `argv=(branch,)` (no numeric token → the op defaults
   amount to 1), and replies the RESULT_CARD `<@u> {message}` mention-prefixed on
   BOTH the success and the business-refusal face (the skill family's
   `skill_respec_route` / `skill_route` posture).
2. **The wiring** — `sb/domain/mining/panels.py`: the four `sk_*` branch buttons
   flip from `HandlerRef("mining.skill_spend_pending")` to
   `mining.skill_spend_route`; the `_skills_button_handlers()` pending-registrar
   is retired (its only remaining entry was the now-ported spend; the ♻ Respec
   entry retired at WP-7), and its `_register_refs()` call removed.
3. **Tests** — `tests/unit/mining/test_mining_skill_spend_button.py` (9 cases):
   each branch button routes to `mining.skill` with `argv=(branch,)` amount-1,
   the RESULT_CARD mention prefix on success + verbatim refusal faces
   (no-points / per-branch-cap), and the session_action → branch derivation.
4. **The golden** — `parity/goldens/mining/mining_skill_spend_write.json`
   (minted per-case via `tools/mint_golden.py mining.skill_spend_write --write`,
   ORACLE-VERIFIED): `!skills` then the ⛏️ Mining click on a level-2 fixture
   spends 1 point (player_skills mining 0→1) and speaks the verbatim allocate
   copy. New curated case in `parity/cases/curated.py`; count pins auto-rewritten
   in `parity/parity.yml` + the two count-pin tests (523→524, minted 61→62).
5. **This card.**

## Trail
- ORACLE (menno420/superbot): `disbot/views/mining/skills_panel.py`
  `MiningSkillsView._spend` (lines 74-104) — each branch button calls
  `skill_service.allocate(guild, user, branch)` with the default `n=1` (spend
  ONE point), then re-renders the embed in place with a `("✅ "|"❌ ") +
  result.message` note. `services/skill_service.py::allocate` (lines 75-113)
  owns the branch/amount/cap/budget validation + the verbatim response strings.
- SB write already ported: `sb/domain/mining/ops.py::_record_skill` (op
  `mining.skill`, WP-5) is the `allocate` verbatim; `_branch_amount_from`
  defaults amount to 1 when no numeric token rides `argv`. The command lane
  (`skill_route`) already drives it and `mining_skill_write.json` pins it.
- DELIVERY seam: session panels mint each button as an ephemeral component whose
  stored args carry `session_action=<action_id>` (`sb/kernel/panels/engine.py`
  `_mint_ephemeral`:388-391), delivered to the handler on click
  (`sb/kernel/interaction/adapters/component.py::dispatch_component`:141-166) —
  the same `req.args["session_action"]` idiom the rps/blackjack session handlers
  read.
- POSTURE (decide-and-flag, sibling-precedent): the reply is a RESULT_CARD
  `<@u> {message}` text card, NOT the oracle's in-place panel re-render — the
  ACCEPTED sb divergence landed by every mining panel-write button
  (`skill_respec_route` WP-7, `vault_deposit_route` / `stash_all_route` #520,
  `forge_build_route` WP-6). The skill family prefixes the mention on BOTH faces
  (unlike the vault lane's bare refusal) — the `skill_route` /
  `skill_respec_route` convention.
- MINT decision (decide-and-flag): a skills-panel button click IS drivable by the
  SB capture harness (`kind="click"` + `component_index`), proven by the landed
  `mining.respec_write` / `mining.stash_all_write` / `mining.build_forge_write`
  click goldens — the no-mint posture is reserved for undrivable MODAL submits
  (B1's vault deposit/withdraw). So this slice MINTS `mining.skill_spend_write`,
  matching every drivable-panel-button-write sibling. Same op the command lane
  pins; player_skills already covered by WP-5, so NO exemption retires.
- Compat: `check_compat_frozen` OK — the branch buttons are session-minted (no
  `custom_id_override`, no `modal_id`), so `legacy_custom_ids` is untouched; no
  command added, so the manifest snapshot is unchanged.
- Verify: `pytest tests/unit/mining/test_mining_skill_spend_button.py` → 9
  passed; full `tests/unit` → 3300 passed, 2 skipped; parity count-pin suites
  (`parity_adapter` + `parity_gate`) green at 524; `check_compat_frozen` → OK.
  No `golden --gate` run (the CAPABILITIES session-window wall) — per-case
  `mint_golden` ORACLE-VERIFY only; full parity verifies in CI.

## 💡 Session idea
The "is B2 already ported?" claim-check is where the real leverage was: the
`mining.skill` WRITE op was already LIVE and golden-pinned via the `!skill`
command lane, which — read shallowly — looks like "already done" (the B1 stash
trap). But a WRITE OP and a WRITE FACE are different deliverables: the panel
button is a distinct user surface that still refused. The tell that settled it
was the corpus itself — `mining.respec_write` / `stash_all_write` /
`build_forge_write` are all drivable-panel-button-write goldens for ops that ALSO
have command lanes, proving the project treats each button face as its own
port-and-pin. A cheap standing heuristic for the next panel-port session: grep
the golden corpus for a sibling that drives the SAME surface class (button vs
modal vs command) before deciding "already ported" or "unmintable" — the corpus
encodes the posture more reliably than the backlog line does.

## ⟲ Previous-session review
🔎 Prev-session review (`.sessions/2026-07-18-capabilities-golden-gate-wall.md`,
`complete`): that session recorded the durable CAPABILITIES fact that full
`tools/run_golden_parity.py --gate` cannot finish inside a session/container
window — full parity is a CI-only gate, and `tools/mint_golden.py <case_id>` is
the only granular local oracle check. This slice is the direct beneficiary: it
is an oracle PORT that needed exactly one golden, so it reached straight for
per-case `mint_golden` (dry-run → ORACLE-VERIFY → `--write`) and never attempted
the `--gate` wall — turning the prior card's recorded wall into an operating
constraint honored from the first step, with the full corpus left to verify in
CI. The prior card's guard recipe worked as intended.

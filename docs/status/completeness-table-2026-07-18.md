# Completeness reconciliation snapshot — 2026-07-18

> **Status:** `reference` — a verify-first reconciliation of the per-subsystem
> completeness ledger. **SUPERSEDES** the stale
> [`docs/status/completeness-table-2026-07-13.md`](completeness-table-2026-07-13.md).
> Point-in-time, derived from a shallow oracle clone; regenerate rather than amend.

## What this is

The 07-13 table drifted: rows it lists as pending have since landed, and a
handful of its remaining flags were mis-scoped (byte-faithful oracle stubs read
as gaps). This snapshot reconciles the backlog against ground truth by an
**oracle-vs-HEAD pass** run this session — every verdict below was hand-verified
by reading BOTH sides:

- **live oracle** — `menno420/superbot @ 69a061d` (the shipped Discord bot,
  the port's parity target).
- **superbot-next HEAD** — `782ca2d` (the base this snapshot branched from is
  the same commit; where a later base is used, both should be noted — here
  base == oracle-compared HEAD == `782ca2d`).

It is a docs-only planning artifact: no `sb/` code changed. Evidence citations
are `file:line` at HEAD `782ca2d` unless noted.

## Method (evidence-first)

For each backlog item the 07-13 table (and the intervening scout notes) left
open, both sides were read in source: the oracle handler/view and the sb port.
An item is **DONE** when the sb port routes to a real audited write (goldens
cited); **NOT-A-GAP** when the oracle itself ships a stub/placeholder/refusal
and sb reproduces it byte-faithfully; **OPEN** when a real oracle write has no
live sb equivalent behind the panel. OPEN items carry a **mintability** call —
whether porting is a small re-point-plus-golden ("mintable") or needs a new
seam / subsystem / owner action.

## DONE / NOT-A-GAP — were stale-listed as pending

| Item | Verdict | Evidence (HEAD `782ca2d` vs oracle `69a061d`) |
|---|---|---|
| **B4** mining `!cook`/`!use` energy lane | **DONE (live)** | `sb/domain/mining/service.py:1113-1211` `cook_route`/`use_route` → audited `_record_cook` / `_record_use_item` real writes; `PENDING={}` empty. Goldens: `mining_cook_campfire_write`, `mining_use_*`. |
| **B5** fishing deep-system + minigame | **DONE** | PENDING roster empty (`sb/domain/fishing/service.py:1597`); cast-again wired to `fishing.cast_open` (`panels.py:412`); real-time bite/reel timing gate reproduced deterministically on the logical clock (spook/grace/too-slow/trophy-fight). 8 pinning goldens (`fishing_cast_*`). The backlog "cast-again dead" claim was STALE. |
| **B6** settings admin-audit surface | **DONE** | All 5 hub buttons armed with explicit PanelRefs (`sb/domain/settings/panels.py:336-348`: needs_setup / invalid / missing_bindings / audit / command_access incl. live `ca_mode`/`ca_channels` writes); access explorer armed. The `settings.{action_id}_pending` default (`panels.py:300`) is now dead/unreachable. Scout's "9 actions + 2 selectors pending" was stale. Residual `settings.group_pending` (per-group scalar EDIT page) is a SEPARATE settings-mutation write slice — see OPEN. |
| **B7** xp.config panel (4 actions) | **DONE** | Landed earlier (noted DONE in #523). Handlers `sb/domain/xp/handlers.py:159-250`, manifest `sb/manifest/xp.py:156`, 25/25 tests, golden-pinned. |
| **B11** server_management availability projection axis-5 | **NOT-A-GAP** | The oracle's own axis 5 is an identical "skipped / availability policy not implemented" stub (`disbot/services/access_projection.py:439-448`); sb ports it byte-faithfully (`sb/domain/server_management/access_projection.py:480-493`). Nothing to port. |
| **C2** effect-leg compensation | **DONE** | #105 + moderation parity flip; empty `_ALLOWLIST` invariant green. |
| **C3** ensure-only registration | **DONE** | #508; empty `_KNOWN_ENSURE_ONLY` frozenset. |
| **C5** setup compound-op apply seams | **NOT-A-GAP** | Landed 2026-07-13 compound-ops slice: `create_channel`→`setup.ensure_channel`, `create_managed_role`→`role.create_managed_role`, `set_cog_routing`→`routing.set_policy`, `add_rule`→`automation.add_rule` all bind real effect legs and apply via final_review's K9 `DraftPipeline` (`sb/domain/setup/final_review.py:397`); windowed cog-select DONE (`cog_routing.py:455` `windowed=True` `page_size=25`). Residual was a STALE docstring only at `sb/domain/setup/wizard.py:106-113` — since fixed by #526 (see the DONE `setup docstring` row). |
| **casino roulette** | **NOT-A-GAP** | Oracle ships roulette as a disabled "coming soon" placeholder (`disbot/views/casino/hub.py:101-118`); sb returns the identical byte (`sb/domain/casino/service.py:95-99`). |
| **cleanup `!cleanuphistory`** | **NOT-A-GAP** (honest gated under-port) | Oracle runs it live (`disbot/cogs/cleanup_cog.py:321-491`); sb ports the `prohibited` matcher for real and returns DECLARED BLOCKED refusals for the history-read + deletion legs (`sb/domain/cleanup/handlers.py:137-190`), never a silent partial sweep. Full parity awaits the discord-adapter channel-ops / history-reader slice. |
| **utility Invite** | **DONE** | `sb/domain/utility/handlers.py:436-457` real `actions.create_invite(max_uses=1, unique=True)`, matches oracle `utility_cog.py:290-295`. |
| **C1** setup-band except-density audit | **DONE** | Closed AFTER this snapshot's base — was mis-listed PARTIAL. Every `except Exception` in the setup band now carries characterization coverage under `tests/unit/setup_band/`, landed across four legs: #516 (`7ceedee`) + #519 (`eb2f146`) characterized moderation + count/list soft-fail, then #526 (`0cac02d`, final_review/essential boundaries) + #538 (`bfff394`, launcher/wizard — "finish C1 audit"). `git log bfff394..HEAD -- sb/domain/setup/` is EMPTY — no new uncovered sites landed after the audit closed. |
| **setup docstring** (C5 residual doc-fix) | **DONE** | Closed AFTER this snapshot's base — was mis-listed OPEN. #526 (`0cac02d`) rewrote the stale `sb/domain/setup/wizard.py:106-113` docstring (the "skipped until their seams exist" text → the resolved "lane is CLOSED / RESOLVED" wording); `grep "skipped until" sb/domain/setup/wizard.py` now returns nothing. |
| **B2** mining skill-panel spend | **DONE (live)** | Closed AFTER this snapshot's base — was mis-listed OPEN/MINTABLE. #527 (`1e61fe6`) re-pointed the four `sk_*` buttons from the pending terminal to `mining.skill_spend_route` → `mining.skill` → the audited spend write (`sb/domain/mining/panels.py:797-811`). Golden `parity/goldens/mining/mining_skill_spend_write.json` + `tests/unit/mining/test_mining_skill_spend_button.py` present. |
| **B3** mining workshop craft selector | **DONE (live)** | Closed AFTER this snapshot's base — was mis-listed OPEN/MINTABLE. #532 (`cae15f8`) wired the `ws_craft` selector → `mining.workshop_craft_pick` → the audited `mining.craft` write (selector `sb/domain/mining/panels.py:1240-1241`, handler `:1172-1242`). Golden `parity/goldens/mining/mining_workshop_craft_write.json` + `tests/unit/mining/test_mining_workshop_craft.py` present. |

## GENUINELY OPEN — remaining work

| Item | Verdict | Mintable? | Evidence + notes |
|---|---|---|---|
| **settings.group_pending** | **OPEN** | MULTI-SLICE EPIC (not a single mint) | The per-group type-specific scalar EDIT page surface — a **page frame** (S0, the ~626-line edit page) + **7 unported edit-widget slices** (bool / enum / number-modal / text-modal / channel / role / numeric-presets). Oracle `menno420/superbot @ f87fa50`: `disbot/views/settings/subsystem_view.py` + `edit_*.py` + `reset_button.py`. Distinct from the (DONE) audit surface. **Large but buildable, NOT blocked:** the write ops already exist (`settings.set_scalar` / `clear_scalar`) and the panel machinery (modals, windowed selects) exists — the cost is breadth (~1800 lines of oracle behaviour), not a missing seam. **Carries an unresolved OWNER-LEVEL product decision** routed to `docs/question-router.md` (append-only owner-intent venue): the oracle opens this edit page for ALL groups uniformly, but the port diverged (5 groups → operator-spine hub, the rest → `group_pending`) — so porting forces whether the edit page replaces `group_pending` for non-hub groups only, or also becomes reachable for the 5 hub groups. That routing choice is owner product-intent, not a worker call. |
| **B10** role-hub route-origin back-button | **OPEN** | decision-sized, NOT cleanly mintable | Oracle appends a dynamic "↩ Server Management" back button per navigation origin (`disbot/views/server_management/hub.py:96`); sb uses only a static `home_hub` / `FOLLOW_PARENT` (`sb/domain/role/panels.py:172`, panel engine `sb/kernel/panels/registry.py:161`). Porting needs a new panel-engine route-origin signal (session-scoped opened-from tracking). |
| **B8** ux_lab 9 wing interiors | **OPEN** | LOW priority | Admin-only (`audience_tier=administrator`), zero-write dev/diagnostic surface; all 9 `*_wing` are honest pending refusals (`sb/domain/ux_lab/handlers.py:50-62`) fronting a fully-ported home panel. Slice foundation-first: (0) port `utils/ux_patterns` registry + `ExhibitWingView` browser grammar, then per-wing — embeds cleanest/mintable; buttons/selects/mock_studio/compare/modals mintable renders; pil_cards/probe_bench/components_v2 need special handling (image bytes / version+date+live-errors / channel-side CV2 + external URLs). No user-facing gap (honest refusals). |
| **btd6** NK bracket standings | **OPEN** | NOT mintable | Oracle has a real live leaderboard (`disbot/cogs/btd6_events_cog.py:72-82`); sb ships an honest named-successor refusal (`sb/domain/btd6/service.py:308-348`, stamped in that module). Needs external Ninja-Kiwi data ingestion (a subsystem, not a mint). |

## OWNER-GATED / SIBLING / FORWARD — not agent-actionable now

| Item | Lane |
|---|---|
| **B1** mining vault deposit/withdraw | Sibling PR #520 (wired at HEAD `sb/domain/mining/panels.py:648,663`). |
| **B9** help editor home message | Sibling PR #512 (OPEN, `sb/domain/help/editor.py:301,613`). |
| **C4** tournament open-flag TOCTOU | **OWNER-DECISION**: `docs/ideas/tournament-open-flag-toctou-2026-07-12.md` `outcome: accepted-posture` (deliberately matches the oracle's non-atomic guard + boot-sweep recovery). Non-atomic guard still present at HEAD (`rps/handlers.py:280`, `blackjack/handlers.py:344`, `tournament_flag.py:112`). Sibling branch `claude/tournament-open-toctou` exists, no open PR. Do not harden without an owner call. |
| **A1/A2/A3, ai NL lane, hermes egress** | OWNER-ONLY (env/creds dark: `ANTHROPIC_API_KEY` / `CLAUDE_ROUTINE_*`). Route to owner queue. |
| **D1–D6** | Forward/planning ideas (themed renderer, real-time minigame framework, access-matrix/audit dashboard, observability/metrics, e2e/live-guild harness, autonomy-apparatus removal). Design-first. |

## Conclusion

The user-facing port surface is **essentially exhausted.** The small mintable
re-points are now closed — B2/B3 (mining skill-spend / workshop-craft, #527/#532)
have since landed and moved to the DONE table, joining C1 and the `wizard.py`
docstring fix (#526/#538). What remains OPEN is no longer single-mint work: one
LOW-priority larger surface (**B8** ux_lab, an admin-only zero-write dev tool),
the **settings.group_pending** per-group edit-page EPIC (multi-slice + an
owner-gated group-routing decision routed to `docs/question-router.md`), and two
non-mintable / decision-or-ingestion items (**B10** route-origin engine signal;
**btd6** NK ingestion). Nothing on the OPEN list is a silent user-facing gap:
the remaining pending terminals are honest declared refusals, and the NOT-A-GAP
rows are byte-faithful oracle stubs.

**Recommendation:** shift the loop toward **PLANNING mode** — turn D1–D6 into
fuller design docs — with the mintable mining lane now cleared. Honestly: this
snapshot is itself point-in-time and derived from a shallow oracle clone; treat
it as a dated checkpoint to be regenerated next wave, not a standing source of
truth.

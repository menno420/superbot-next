# Sim-lab review — superbot-next's evidence seat, audited (2026-07-12)

> **Status:** `audit` — point-in-time review of the sibling sim-lab project
> (menno420/sim-lab) from this repo's seat: what it is, whether its output is
> trustworthy and current, and what happened to its findings about this repo.
>
> **Provenance.** Researched 2026-07-12, read-only on the sim-lab side.
> Sim-lab cites are at its HEAD `055245e` (last push 2026-07-12T10:36Z);
> superbot-next cites are at main `dd76427` (#262) unless flagged. VERDICT
> 009's headline findings were re-verified against this repo's code at that
> HEAD, not replayed from the verdict's pinned (and now stale) snapshot.
> Model attribution family-level only; anything unverifiable is marked
> "not measured".

## 1. What sim-lab is

Sim-lab is the fleet's **evidence seat**: a substrate-kit-managed lane that
settles build-worthy ideas with reproducible evidence (numeric simulations,
measured prototypes, benchmarks) and publishes finalized **verdicts**
(approve / reject / needs-more-evidence) to its own append-only outbox. It
explicitly "does **not** build products, does **not** dispatch work to
lanes, and its only writable repo is this one" (sim-lab `README.md:10-15` @
`055245e`). Pipeline position: idea-engine generates → sim-lab reproduces
evidence and finalizes → the fleet manager final-reviews and routes ORDERs →
lanes build (`README.md:17-19`). Its method contract is a three-rung
"method ladder" (numeric simulation → measured prototype → JUDGMENT-ONLY
analysis, the label travels with the verdict; `README.md:21-32`), a
five-question validity gate (comparable / uncorrupted / robust /
reproducible / limits; `README.md:34-45`), and a fixed verdict grammar for
outbox entries (`README.md:47-64`).

**Critical distinction — sim-lab is NOT this repo's sim gate.** The two
systems share the word "sim" and nothing else:

- **This repo's sim gate is internal.** `sim/` (space.py, run.py, apply.py,
  oracles/, records/, `sim-gate-baseline.json`) plus `tools/check_sim_gate.py`
  are superbot-next's own layer-V arrangement machinery, built to design-spec
  §2.10 (the layer-V build decision, `docs/decisions.md:147`). Nothing in
  this repo imports or consumes sim-lab artifacts: a repo-wide grep for
  "sim-lab" (excluding kit machinery) hits only fleet-coordination prose —
  the program review's provenance line, this directory's README, two
  status.md incident mentions, and one retro (`docs/review/program-review-2026-07-12.md:7`,
  `docs/review/README.md:5`, `control/status.md:109`, `control/status.md:243`,
  `docs/retro/q0265-routine-loop-2026-07-11.md:31`). None is a data
  dependency.
- **Sim-lab has never produced a baseline, overlay, `sim/records/` entry,
  or SimRef for this repo** (verified both directions: this repo's
  `sim/records/` holds only its README; sim-lab's tree contains no
  superbot-next lock/baseline artifact). The naming trap runs the other way
  too: the program review's section "What the sim lab and backlog say"
  (`docs/review/program-review-2026-07-12.md:400-409`) is about this repo's
  OWN `sim/` machinery, not the sim-lab repo.

Structure at `055245e`: `sims/` (13 one-idea subtrees + a worked exemplar),
`harness/` (reusable helpers, ~214-line `simharness.py` + selftest),
`control/` (inbox / append-only outbox / status heartbeat), `docs/`,
15 session cards, 2 CI workflows, plus kit machinery.

## 2. Is it good, and is it current?

**Active today.** 53 commits from seed (2026-07-10T19:17Z) to HEAD
(2026-07-12T10:36Z — last push the day of this review); a single-owner,
agent-operated lane where every change lands via squash-merged PR (#1–#52).
Currently idle only because its intake queue is empty: "Sim-ready intake
queue EMPTY (consumed through PROPOSAL 011 → VERDICT 013). 13 verdicts
finalized (V001–V013)." (sim-lab `control/status.md:4`, health green,
updated 2026-07-12T10:34Z).

**CI green, but hygiene-only.** Two workflows (kit hygiene gate +
auto-merge enabler); the 15 most recent runs on 2026-07-12 all completed
green (GitHub Actions API, 110 total runs). Note: **CI does not run the
sims** — sims are verified by their own documented commands pre-push
(sim-lab `README.md:93-94`).

**All 13 sims are real; zero stubs.** Every sim's documented command was
re-executed locally on 2026-07-12: all 13 (plus the harness selftest) exit
0 with passing self-check batteries — e.g. the settings-UX sim
(`sims/owner-001-superbot-next-settings-ux/settings_ux_sim.py`, 737 lines)
reports "SELF-CHECKS: 556 passed, 0 failed" with byte-identical results on
re-run; the largest battery (verdict-008) passes 7723/0. All are
stdlib-only and deterministic (seeded or byte-identical-rerun asserted),
each with README + REPORT. The lane also publishes honest negatives — its
newest verdict (V013) rejects building the very checker it was asked to
evaluate ("do NOT build check_copy_drift.py — apply the one-line fix",
sim-lab `control/outbox.md:150`).

**Currency: per-verdict pinning, no continuous tracking.** Sim-lab pins the
subject repo's SHA per verdict and never re-tracks. Consequences at this
repo's HEAD:

- VERDICT 009's pin `168ef80` (2026-07-11, PR #185 era) is **stale and
  orphaned**: 50+ commits behind, and `git merge-base --is-ancestor` fails —
  the pinned snapshot sits on a since-replaced merge line of main (no remote
  branch contains it).
- VERDICT 013's pin `af985c17` (2026-07-12) **is** an ancestor of current
  main — only hours old at verdict time.

So verdict findings decay at this repo's merge rate, and nothing on either
side re-audits them — which is exactly how §4's situation arose.

**Known walls** (sim-lab `control/status.md` owner-actions;
`PLATFORM-LIMITS.md`): the Codex second-eyes loop is dead in practice
(usage-capped; the single reply that ever landed, on V012, was rejected as
fabricated — "no such commit/branch/PR exists anywhere", sim-lab
`control/outbox.md:139`), the review site is undeployed, and tag pushes 403.

## 3. The verdict ledger — all 13

All finalized verdicts live in sim-lab `control/outbox.md` (append-only).
Dates UTC; the four **superbot-next-targeted** verdicts are marked ●.

| # | Date | Target | Verdict |
|---|------|--------|---------|
| V001 | 2026-07-10 | superbot (Encounters cog) | needs-more-evidence |
| V002 | 2026-07-10 | idea-engine (probe battery) | approve-selectively |
| V003 | 2026-07-10 | websites lane + superbot API (OAuth trust gate) | needs-more-evidence |
| V004 | 2026-07-10 | superbot (explore-hub XP) | needs-more-evidence |
| V005 | 2026-07-10 | substrate-kit (capability self-probe) | needs-more-evidence |
| V006 | 2026-07-11 | superbot-idle (idle economy) | approve |
| V007 | 2026-07-11 | product-forge (games-web phase 2) | needs-more-evidence (redirect) |
| V008 | 2026-07-11 | superbot (mining-grid encounters) | needs-more-evidence |
| ● V009 | 2026-07-11 | **superbot-next (settings/UX + AI panel)** | needs-more-evidence — "approve-the-direction + ship the named changes" |
| ● V010 | 2026-07-11 | **superbot-next (settle-once fence)** + superbot one-liner | approve (contract c) |
| V011 | 2026-07-11 | menno420/websites (4-site audit) | approve |
| ● V012 | 2026-07-12 | **superbot-next (doc-cite checker spec)** | approve |
| ● V013 | 2026-07-12 | **superbot-next (oracle copy drift)** | reject the checker; apply the one-line fix |

(Reports live under sim-lab `sims/<name>/REPORT.md`; outbox line anchors
for each entry are in `control/outbox.md:11-153` @ `055245e`.)

## 4. The unconsumed findings — the owner's suspicion, confirmed

**VERDICT 009** (sim-lab `sims/owner-001-superbot-next-settings-ux/REPORT.md`,
finalized 2026-07-11T15:16Z, outbox `control/outbox.md:95-105`) is the
owner-directed settings/commands/UX + AI-panel review of this repo, pinned
at `168ef80`. Its measured headlines: settings NEW 125 vs OLD 118, commands
367 vs 484; **19 display-only settings** (all of `image_moderation` (8) +
`security` (11) — rendered by panels, read by no enforcement engine — its
"headline defect"); **8 dead settings** (no reader at all); a
discoverability WIN (125/125 = 100% reachable from `/settings` vs OLD
108/118); and an independent AI-panel audit of 8 findings (AIP-01..08,
3 high / 4 medium / 1 low, each cited file:line).

**Nothing in this repo ever consumed it.** Verified at HEAD: repo-wide
searches (excluding kit machinery) for `owner-001`, `VERDICT 009`, and
`AIP-` return **zero hits** in files, `git log --all`, inbox ORDERs, and
status acks. No inbox ORDER routes any sim-lab finding here
(`control/inbox.md:1-135`, ORDERs 001–015 — zero sim-lab mentions), and the
2026-07-12 program review does not cite it. One finding (AIP-01) was fixed
anyway — by this repo's own band-7 parity work, which nowhere references
the verdict. Independent convergence, not consumption.

### V009 headline findings, re-verified at HEAD `dd76427`

| Finding (V009, pinned `168ef80`) | Status at HEAD | Evidence |
|---|---|---|
| **AIP-01 (high)** — Tools chooser entirely non-functional; all 4 buttons dead-end to `chooser_scope_pending` (then `sb/domain/ai/panels.py:434-439`) | **FIXED since** — by the routing-matrix slice of the band-7 parity lane (2026-07-11, `docs/decisions.md:549`), which retired the pending terminal; sim-lab is not referenced | All chooser scope buttons now route to live pickers; the terminal survives only as a comment: "The `chooser_scope_pending` terminal retired … (no button routes to it anymore)" (`sb/domain/ai/settings_widgets.py:355-363`); the hardcoded "overrides: 0 channel · 0 category" string (AIP-05) is likewise gone from `sb/domain/ai/` |
| **AIP-02 (high)** — operator cards (`ai.card`) render no back/home/help; Diagnostics/Providers/Routing + Preview flows strand the operator (then `panels.py:206-207`) | **STILL PRESENT** | The `ai.card` spec pins `navigation=NavigationSpec(show_help=False, show_home=False)` with zero components (`sb/domain/ai/panels.py:216-235`); every operator card renders as a bare embed via `_card` (`sb/domain/ai/service.py:38-48`). The in-code justification frames this as parity with the shipped `ctx.send(embed=…)` reply — deliberate, but the UX finding stands |
| **AIP-03 (high)** — doubled prefix in every settings ack/prompt: shows `ai.ai_enabled` while the same embed prints `ai_enabled` (then `panels.py:825-829`) | **STILL PRESENT** | Acks/prompts prefix `ai.` onto the *persisted key* rather than the spec name: the widget key is the settings_key ("the select option values are the shipped `spec.name` strings = our settings_key", `sb/domain/ai/settings_widgets.py:60-68`), so `ai_enabled` (`sb/domain/ai/settings_schema.py:29`) acks as `` `ai.ai_enabled` `` (`sb/domain/ai/settings_widgets.py:172`, `:182-185`, `:341-352`; prompt copy `sb/domain/ai/panels.py:1360`, `:1364`, `:1398-1414`) |
| **19 display-only settings** — all of `image_moderation` (8) + `security` (11), wired only to panel rendering | **STILL PRESENT** (spot-checked 3 of 19) | `sb/domain/image_moderation/` contains only `__init__.py` + `panels.py` — no engine; grep over `sb/kernel/`, `sb/adapters/`, `sb/app/` finds zero readers of either family's keys. The manifest self-declares the future: "The scan engine arms with the message band + provider keys" (`sb/manifest/image_moderation.py:1-5`). Security raid/age settings are read only at panel render (`sb/domain/security/panels.py:96-112`) — no join listener, no slowmode enforcement anywhere |
| **8 dead settings** (no reader): `ai.audit_log_channel`, `btd6_strategy_submission_channel`, `cleanup_spam_window_seconds`, `deathmatch_turn_timeout`, `moderation.public_log`, `skip_roles`, `welcome_card_enabled`, `welcome_min_account_age_days` | **STILL PRESENT** (spot-checked 2 of 8) | `deathmatch_turn_timeout`: declared (`sb/manifest/deathmatch.py:22-23`), zero readers — even after the deathmatch parity birth (#261). `cleanup_spam_window_seconds`: declared (`sb/manifest/cleanup.py:55-56`), zero readers (automod's same-named key is a *different* setting with a real engine reader, `sb/domain/automod/engine.py:95`). `skip_roles` and `welcome_card_enabled` also show declaration-only grep profiles; the remaining 4 were not re-audited (not measured) |

### The other three superbot-next verdicts — consumed?

- **V010** (approve — build a settle-once fence over the op grammar,
  contract (c): row-consumption + mandated check-and-set for no-row legs):
  **not consumed.** No settle-once checker exists in `tools/` and nothing
  references the verdict. Adjacent-but-different work happened
  independently: `tools/check_money_race.py` (#221, 2026-07-12) is the
  F-001/F-002 locking-class lint born from this repo's own wallet-race arc
  (#213/#217/#223), not V010's settle-exactly-once contract.
- **V012** (approve — ship `tools/check_doc_cites.py` per the measured
  spec, 0 FP on this repo's corpus): **not consumed.** No such tool exists
  in `tools/` and no ci.yml wiring references it.
- **V013** (reject the checker; apply the ONE-LINE fix —
  `sb/domain/rps/tournament.py:153` period → "!"): **not consumed.** The
  line still reads `"You're already registered."` at HEAD (verified
  `sb/domain/rps/tournament.py:153`), diverging from the frozen oracle's
  `"You're already registered!"` — the single true copy-drift its 60-cell
  sweep found.

Score: of 4 superbot-next verdicts, 0 consumed; 1 finding (AIP-01) fixed by
coincidence. The pipeline's last leg — "the fleet manager final-reviews and
routes ORDERs" — has never fired toward this repo.

## 5. Gap analysis — sim-lab vs what this repo needs

This repo's need, per its own program review: "The sim gate is a real
drift tripwire, but zero layouts are sim-backed yet … 788/788 pins are
`Exempt` and 0 carry a simulation reference — `sim/records/` is empty"
(`docs/review/program-review-2026-07-12.md:402-409`, audited at `c792079`).
Re-counted at HEAD: **802 assignments, 802/802 exempt, 0 sim_ref**
(`sim/sim-gate-baseline.json`), `sim/records/` still README-only.

**What sim-lab HAS that is reusable here:**

1. **Harness v0.1** (`harness/simharness.py`, stdlib-only, vendor-copy
   contract — standard 5-seed set, CRN variance reduction, sweep runner,
   self-check battery, determinism checks) + report template + passing
   selftest.
2. **A proven method**: ladder + validity gate + verdict grammar, exercised
   13 times in ~2 days, with honest negatives (V013's self-defeating
   reject).
3. **Settings/panel inventory machinery** (owner-001): settings/commands/
   panels inventory schema with `read_where`/`set_where` file:line arrays,
   dead/display-only detection, a command→panel→setting reachability graph
   with BFS click-distance — directly relevant to panel review, but it
   consumes agent-extracted static JSON, not live renders.
4. **Real-engine-driving precedent** (V006): byte-vendored the subject's
   engine inside the sim and drove it directly ("zero model-vs-engine gap",
   sim-lab `control/outbox.md:72`) — the pattern a sim-backed layout run
   needs.
5. **Live web-crawl capability** (V011) and **checker-spec sweep machinery**
   (V012/V013) over real pinned corpora of both bots.

**What sim-lab is MISSING for sim-backing this repo's layouts:**

1. **No Discord/panel-render simulation** — nothing in sims/ or harness/
   renders or drives Discord UI; panel work is static-inventory analysis
   only (self-flagged in the V009 report's limits).
2. **No live-bot telemetry capture** — a self-flagged standing gap ("no
   users, no telemetry" kept V009's headline UX question JUDGMENT-ONLY);
   this repo's `sim/usage.snapshot.json` is likewise seeded-empty by design
   ("the sim never runs on invented data", `sim/__init__.py`).
3. **No link into this repo's provenance chain** — sim-lab has never
   produced a `sim/records/` entry, a SimRef, or an overlay for
   `sim-gate-baseline.json`. Filling the 0-sim-backed gap would be new
   work; the cheap path per this repo's design is to run this repo's own
   `sim/run.py --space <sim_id>` and let `sim/apply.py` write the locks,
   with sim-lab's established specialty being the *evidence review of
   oracle validity*, not the record-minting itself.
4. **No continuous tracking** — per-verdict pins only (V009's is already
   orphaned); any layout-value evidence would need re-pinning machinery to
   stay valid.

### Cross-reference: the outbound requests doc landed mid-review

`docs/requests/sim-lab-requests-2026-07-12.md` did not exist when this
review's research began (verified at `764a393`: no `docs/requests/`
directory, no open PR, no branch, zero code-search hits anywhere including
sim-lab itself); it landed while this document was being assembled
(#262, merge `dd76427`). Mapping its six asks onto sim-lab's measured
capabilities above:

| Request | Sim-lab today |
|---|---|
| SIM-REQ-1 sim-back the 802 all-exempt pins | Partially equipped: engine-driving precedent (V006) + this repo's own oracles/runner exist; missing gap 3 (no SimRef/records link) — the request's `sim/run.py --space` framing matches the cheap path named above |
| SIM-REQ-2 money-race scale simulation | Well-matched: V010 already modeled exactly this class (4 contracts × 6 instances, exhaustive interleavings) — but as *reconstruction*, not against real Postgres; scale + real-DB drive is new capability |
| SIM-REQ-3 panel interaction flows | Blocked by gap 1: no Discord/panel-render simulation exists; the owner-001 machinery is static-inventory only |
| SIM-REQ-4 rehearse live-ladder rows 8/9 | Blocked by gaps 1–2: no Discord drive, no live telemetry; the deterministic-provider AI leg is closest to feasible today |
| SIM-REQ-5 long-horizon economy balance | Well-matched: V006's idle-economy kernel is precisely this shape (agent population, faucet/sink tracking) — porting it to this repo's economy is incremental |
| SIM-REQ-6 coverage-exploration sims | Feasible with existing sweep machinery (V012/V013 pattern) over this repo's pinned corpus; no new capability class required |

## 6. Recommended actions

1. **Dispose of the still-live V009 findings** as an inbox-consumable
   ticket: wire-or-hide the 19 display-only settings (or ledger them as
   deliberate future surface), remove-or-wire the 8 dead settings, fix
   AIP-03's ack copy (ack the spec name, not the persisted key), and decide
   AIP-02 (bare cards are deliberate parity — either ledger that as the
   ruling or add the nav row). Each item above carries its HEAD file:line.
2. **Apply V013's one-line fix** — `sb/domain/rps/tournament.py:153`
   period → "!" (plus the two optional whitespace restores it names). It is
   a byte-parity divergence from the frozen oracle, found mechanically,
   cost ~one minute.
3. **Create a consumption path for verdicts.** Today the outbox is
   write-only in practice: 4 verdicts targeting this repo, 0 consumed.
   Cheapest fix consistent with the routing doctrine (`docs/requests/README.md`
   — no direct write path between siblings): the manager turns each
   verdict's "recommendation" block into an inbox ORDER here, and this
   repo's session acks it in `control/status.md` like any other ORDER.
4. **Ask sim-lab to re-pin before acting.** V009's pin is orphaned; any
   consumption pass should first re-verify findings at current HEAD (this
   review did exactly that for the headline items — table in §4).
5. **Route the six SIM-REQs with the capability map in §5** so sim-lab can
   sequence them honestly: 5 and 6 are near-term (existing machinery), 1
   and 2 are medium (new integration, established patterns), 3 and 4 need a
   capability sim-lab has never had (Discord/panel drive) — worth an
   explicit needs-more-evidence-style scoping reply rather than silence.

## Not measured

The 4 un-spot-checked dead settings and 16 un-spot-checked display-only
settings at HEAD (sampled 2 and 3 respectively — all sampled items still
present); whether any V009 medium/low finding besides AIP-05's hardcoded
string moved since the pin; the cause of the `168ef80` history-line
replacement; sim-lab's evidence quality beyond re-executing its sims
(labels and hand-audits taken at face value).

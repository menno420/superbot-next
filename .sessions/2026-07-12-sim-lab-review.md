# 2026-07-12 — sim-lab review: the evidence seat audited + VERDICT 009 re-verified at HEAD

> **Status:** `complete`

- **📊 Model:** Fable · high · docs/audit (Q-0194)

## Scope

Owner-directed review of the sibling **sim-lab** project (menno420/sim-lab)
from this repo's seat: what sim-lab is, whether its output is trustworthy
and current, a complete ledger of its 13 verdicts, and — the owner's
suspicion, confirmed — that its superbot-next findings (VERDICT 009:
19 display-only settings, 8 dead settings, 3 high AI-panel defects) were
never consumed here. Every V009 headline finding re-verified against this
repo's code at current HEAD rather than the verdict's stale pin.
Deliverable: `docs/review/sim-lab-review-2026-07-12.md` (badge `audit`) +
index/link lines, this card, one telemetry row. Docs-only — no code, no
parity data, no control/ writes.

## Headline results

- Sim-lab is real and current: 13/13 sims re-executed green (zero stubs),
  CI green (kit hygiene only), last push the day of this review; but it
  pins per-verdict SHAs and never re-tracks — VERDICT 009's pin `168ef80`
  is orphaned off the rewritten main line.
- Consumption score: 4 verdicts target this repo, **0 consumed** (zero
  hits for owner-001 / VERDICT 009 / AIP- in files, `git log --all`,
  ORDERs, acks). AIP-01 was fixed by this repo's own band-7 routing-matrix
  slice without referencing the verdict — convergence, not consumption.
- Re-verified at HEAD `dd76427`: AIP-01 FIXED since; AIP-02, AIP-03, the
  19 display-only settings (3 spot-checked), and the 8 dead settings
  (2 spot-checked) STILL PRESENT; V013's one-line fix
  (`sb/domain/rps/tournament.py:153` period → "!") still unapplied.
- `docs/requests/sim-lab-requests-2026-07-12.md` (#262) landed mid-review;
  the review maps its six SIM-REQs onto sim-lab's measured capabilities
  (5/6 near-term feasible or established-pattern; panel/live-drive asks
  need a capability sim-lab has never had).

## 💡 Session idea

The consumption gap is structural, not accidental: sim-lab's outbox is
append-only and this repo's inbox has one writer (the manager), so a
verdict that the manager never turns into an ORDER simply evaporates — no
surface on either side ever reds. A tiny manager-side invariant ("every
finalized verdict targeting a lane gets an ORDER or an explicit
no-action ruling within N days") would make silence visible; §6.3 of the
review names the cheapest version.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-cross-project-requests.md`, the most recent
completed card at branch time.) Its numbers held at this session's HEAD:
sim baseline 802/802 exempt with zero sim_refs (re-counted from
`sim/sim-gate-baseline.json`), `sim/records/` still README-only, pytest
1733/13 reproduced exactly (including its env recipe — `env-setup.sh` +
the editable hello-plugin install — which this session needed verbatim).
Its 💡 idea (document the cite-by-line-anchor stamp rule for outbound
docs) was applied here preventively: the review cites
`docs/decisions.md:147` / `:549` line anchors instead of restamping
decision IDs, and `bootstrap.py check --strict` reported zero stamp
findings on the first draft. One irony its requests doc could not know:
its SIM-REQ evidence base and this review's independent sim-lab deep dive
agree on every shared number (802 pins, 13 verdicts, the V009 pin
staleness) — two lanes counting the same things separately and matching
is the cheap cross-check working.

## Close-out

Delivered in one docs-only READY PR on this branch: the review doc
(`docs/review/sim-lab-review-2026-07-12.md` — six sections + a
"not measured" footer; every load-bearing claim cited to a sim-lab
path @ `055245e` or a superbot-next path @ `dd76427`), the
`docs/review/README.md` index entry, one link line in
`docs/retro/README.md`, this card, and the telemetry row. Verify at the
branch head: `python3 bootstrap.py check --strict` — zero doc findings
(only the designed born-red card hold, cleared by this flip, plus the
pre-existing control/status.md owner-action advisory untouched by this
PR) and `python3 -m pytest -q` — **1733 passed / 13 skipped**. No code,
no parity data, no control/ writes.

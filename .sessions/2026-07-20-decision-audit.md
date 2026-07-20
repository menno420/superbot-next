# Session — decision-audit pass (D2 DEFER + owner-agenda audit)

> **Status:** `complete`
>
> Born-red: this card was the sole FIRST commit (it held the substrate-gate
> red); the docs/control edits landed in the following commits; this
> `in-progress` → `complete` flip is the deliberate LAST commit.

- **📊 Model:** opus-4.8 · high · decision-audit

## Order

Decision-audit pass, docs/control only. Two jobs under decide-and-flag
(PL-001): (1) answer the last OPEN owner block in `docs/question-router.md` —
the **D2 real-time minigame-framework go/no-go** — as DEFER-until-a-2nd-consumer;
(2) audit the 31-row owner agenda (`docs/design/OWNER-DECISIONS-2026-07-18.md`),
classify each row reversible-and-decidable vs genuinely-owner, adopt the
reversible design-posture rows as recommended, and trim the agenda to the
genuine-owner remainder. No `sb/` source, goldens, or manifests touched.

## Scope

DOCS/CONTROL only. Zero `sb/` source edited; no dependency change (pip-audit
n/a). Records two ledger decisions, flips one router block, annotates one owner
agenda non-destructively, refreshes two forward-facing docs.

## Result

Landed on PR #601 (base main; docs/control only). Files changed beyond this card:

- **`docs/decisions.md`** — appended two ledger entries in the file's
  `status / date / verdict / why / why-not-owner / provenance` shape:
  - **`[D-0100]`** — D2 real-time minigame framework stays DEFERRED. Do not
    build the `RealtimeRound` kernel primitive (`sb/kernel/panels/minigame.py`)
    for fishing alone (exactly one consumer today); when a 2nd real-time minigame
    is on the roadmap, build D2.1 (the pure, zero-churn extraction) FIRST and
    grow the new game onto it. Reversible flip-to-GO the moment a 2nd consumer
    appears.
  - **`[D-0101]`** — OWNER-DECISIONS 2026-07-18 agenda audit. 9 reversible
    design-posture rows (1, 2, 3, 4, 6, 11, 12, 13, 29) ADOPTED as recommended;
    rows 14–17 subsumed by D-0098, 18–21 by D-0100, 28 already D-0092; 13 rows
    RETAINED as genuinely-owner.
- **`docs/question-router.md`** — the D2 block flipped **OPEN → ANSWERED (DEFER,
  2026-07-20)** (status line, Maintainer answer, Routing result) and moved from
  Open questions to the top of the Answered section. The Open-questions preamble
  rewritten to state **ZERO** open owner blocks remain (D2 was the last).
- **`docs/design/OWNER-DECISIONS-2026-07-18.md`** — non-destructive: a dated
  `> **Audit 2026-07-20:**` banner + a new `## Remaining owner agenda (13 rows,
  2026-07-20)` section listing only the 13 genuinely-owner rows with their
  bolded recs pulled verbatim-in-spirit from each row's detail; the historical
  31-row table retained unedited, each decided/subsumed row marked inline
  (`✅ DECIDED (D-0101)` ×9, `✅ DEFER (D-0098)` ×4, `✅ DEFER (D-0100)` ×4;
  row 28 left as-is).
- **`docs/NEXT-TASKS.md`** — D2 marked DECIDED — DEFER-until-2nd-consumer; noted
  the router now has ZERO open owner blocks; added an honest
  `## Executable backlog (2026-07-20 audit)` section (HONESTY GUARD: no contained
  honest build slice is unblocked today; remainder owner-gated / awaits a real
  consumer).
- **`control/status.md`** — heartbeat factual fields only (updated / phase /
  last-shipped #600 / open-prs / next-2 / blockers). The RETIRED banner and ALL
  wake-chain / trigger / routine text left verbatim (classifier-sensitive).
- **`control/claims/decision-audit-2026-07-20.md`** — the work claim.

**Decision flagged (decide-and-flag, PL-001):** the coordinator dispatch asked
for the two new `D-NNNN` ids to be cited across `question-router.md`,
`OWNER-DECISIONS-2026-07-18.md`, `NEXT-TASKS.md`, and this card. The required
`substrate-gate` / `check_stamp_discipline` gate (bootstrap.py:5618) forbids a
`D-NNNN` id from appearing in **more than one non-ledger `.md` under `docs/`**
(the ledger `docs/decisions.md` is exempt; `control/status.md` is outside
`docs/` so exempt too) — and `tests/test_session_card_gate.py::test_added_complete_card_passes`
enforces it as an exit-affecting gate that reds the pytest lane. A literal
reading REDs a required gate. Reconciled: each new id is stamped at ONE home —
the ledger plus at most one non-ledger doc (`OWNER-DECISIONS-2026-07-18.md`,
which carries the table markers). `question-router.md` and `NEXT-TASKS.md` refer
to the decisions in **prose** (ledger pointer + date), exactly the convention
the prior B10/S6 defer PR used. Reversible if the owner wants the ids spelled
out per-doc — but only by relaxing the gate.

## Verification

- `python3 -m pytest -q --ignore=examples` → **3660 passed, 54 skipped, 1
  warning** in ~67s. The 1 warning is the pre-existing `discord/player.py`
  `audioop` DeprecationWarning (stdlib, unrelated). The stamp-gate test
  (`tests/test_session_card_gate.py`) is green after the one-home reconciliation.
- `python3 bootstrap.py check --strict --status-only` → **control-status check
  passed** (exit 0). Advisory-only warnings (owner-action-fields on
  control/status.md, claims-format on THREE *other* pre-existing claim files, a
  stale claim, seat-digest, automerge-branch-drift) are pre-existing and never
  exit-affecting.
- Per-id stamp spread verified: D-0092 (ideas/tournament), D-0098 / D-0100 /
  D-0101 (OWNER-DECISIONS only), D-0099 (zero non-ledger) — each ≤1 non-ledger
  doc.
- `git diff --name-only origin/main` touches only `.sessions/`, `docs/`,
  `control/`, and the `.substrate/guard-fires.jsonl` telemetry delta. **No `sb/`
  source, goldens, or manifests.**

## 💡 Session idea

The load-bearing surprise this slice surfaced is that **"cross-reference the
decision everywhere" and "stamp each decision at one home" are in direct,
CI-enforced tension** — and the honest resolution is not to pick one but to
split the two jobs a decision id does. An id has a *canonical* job (the ledger
entry that IS the decision) and a *navigational* job (every doc that wants to
point a reader at it). The stamp gate exists because the second job, done with
the literal token, silently forks truth: when the decision changes, every
non-ledger copy of `D-0100` is a stale claim nobody re-reads. The gate's fix is
to let prose do the navigating ("recorded in the decisions ledger, 2026-07-20")
while the token stays unique — a pointer that cannot go stale because it names
no volatile fact. The reusable rule for any future decision-recording slice:
**mint the `D-NNNN` token in `docs/decisions.md`, allow it in at most ONE
non-ledger doc (the one whose primary job is to track dispositions — here the
owner agenda's inline table), and everywhere else navigate by prose + date.**
The corollary that makes it cheap to obey: run `bootstrap.py check --strict`
(or just `tests/test_session_card_gate.py`) BEFORE the first commit of any
multi-doc decision slice — the gate names the exact over-citations in seconds,
so the reconciliation is a find-and-prose pass, not a re-derivation. A dispatch
that asks for tokens-everywhere is asking for the navigational job; deliver it
as prose and the canonical job stays singular.

## ⟲ Review

### previous-session review

Predecessor: `.sessions/2026-07-19-coercion-sweep-panels.md` (`complete`,
`opus-4.8 · high · test writing`) — the TRUE-final display-renderer slice of the
domain-coercion sweep, landed as #600 (the `last-shipped` this card's heartbeat
now advances to). Its conventions carried here byte-for-byte: a born-red card as
the sole first commit holding the substrate-gate, the substantive edits in
following commits, the `in-progress → complete` flip as the deliberate last
commit; a Verification section re-running the exact command with the verbatim
count (its 3712/2-skip vs this slice's 3660/54-skip — the delta is the two
suites diverging on the Postgres/discord availability in each environment, not a
regression: this run's failure-then-green was the stamp gate, fixed in-slice,
not a test count drift); and the honesty seam — assert/record only what is truly
there. Where this slice diverges: the coercion sweeps were *test-only* additive
work with zero decision content, whereas this is a *docs/control* decision-audit
with zero test content — the mirror-image slice. The shared spine is the
born-red discipline and the "route the friction to the idea, don't smuggle it
into the change" habit: the coercion card routed its helper-scatter cleanup to
its 💡 rather than fixing it; this card routes the stamp-gate-vs-cross-reference
tension to its 💡 rather than relaxing the gate. Both close as low-risk,
gate-green, single-purpose slices because the analysis was done honestly before
the commit.

# 2026-07-18 — complete owner-agenda rows 22/24/25 from now-merged D5/B8/R docs

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · medium · docs · complete owner-agenda rows 22/24/25 from now-merged D5/B8/R design docs (born-red, holds substrate-gate)

## Scope

The consolidated owner-decision agenda (`docs/design/OWNER-DECISIONS-2026-07-18.md`,
#539) was written just before three design docs merged, so its intro + three rows
(22 B8, 24 D5, 25 R) carried a stale "source doc pending" caveat and cited framing
(the completeness table + backlog) rather than the real docs. Those docs are now on
`main` — D5 (#533), B8 (#531), R (#535) — so this slice upgrades the three affected
blocks + summary-table rows to reflect the ACTUAL "Open questions for the owner"
from the now-present docs, each with a real recommendation, the specific slice it
unblocks, and a `Source:` link to the merged doc.

Docs-only planning-artifact edit — no `sb/` code changes. Grounded in the three
docs' own open-questions sections read at HEAD `add707d`.

## Deliver

- `docs/design/OWNER-DECISIONS-2026-07-18.md`:
  - **Row 22 (B8)** upgraded to the doc's real 5 questions — including its **5th**
    (registry home: `sb/spec/*` vs `sb/domain/ux_lab/*`) the placeholder row omitted;
    `Source:` → `B8-ux-lab-wings.md`; drops the "design doc pending" flag.
  - **Row 24 (D5)** upgraded to the doc's **7** real questions — including the
    **degraded-health-vs-block** pass/fail threshold (Q4) and the **automated-run
    `verified_live` signer** (Q6) the placeholder row summarized away;
    `Source:` → `D5-e2e-test-harness.md`; drops the `source doc pending` flag.
  - **Row 25 (R)** framing corrected to the doc's finding: the outbox ALREADY ships
    bounded exponential backoff + a 90d `DEAD` dead-letter + metrics — the real gap
    is the **delivery-ACK boundary** (the retry wraps `bus.emit` = publish-accepted-
    not-delivered; the effectful Discord subscriber swallows its own `HTTPException`)
    **plus DB reconnect/breaker/boot-retry**, NOT "add capped backoff / DLQ 30-day".
    DLQ retention kept at **90d**; `Source:` → `R-resilience-delivery-and-db.md`.
  - Intro "Sources gathered" note: the "D5/B8/R not yet on `main` … source doc
    pending" caveat removed; the D5/B8/R doc links added to the sources line.
  - The other 28 rows are untouched (no renumber, no content change).

## Verification

- `python3 bootstrap.py check --strict` → 0 exit-affecting findings (badges valid +
  all three new `Source:` links resolve now that the docs are on `main`); the only
  red in CI is this card's own designed born-red hold on the substrate-gate until the
  card flips complete.
- No `sb/` or test code touched — docs-only; the functional CI gates ride green,
  substrate-gate is the expected sole hold.

## 💡 Session idea

The agenda was deliberately shipped BEFORE its three source docs landed, with
honest `[?]` "source doc pending" flags and reasonable defaults standing in — a
"write the agenda now, upgrade verbatim when the doc lands" pattern. This session is
the second half of that contract, and it exposes the value of the flag: the
placeholder rows had drifted from the docs in exactly the ways that matter. Row 25
(R) is the sharpest case — the placeholder recommended "add capped backoff / DLQ
30-day" as if the durability spine were greenfield, but R's grounding pass found the
outbox already ships bounded backoff + a 90d dead-letter; the real gap is one layer
up at the delivery-ACK boundary. A summarized-from-framing row can invert the actual
finding, so the "upgrade verbatim from the doc" step is not cosmetic — it is where
the honest recommendation is recovered.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-design-resilience.md` (#535), the last of the three
docs this card consumes, plus the D2/D4 planning-series cards. All were docs-only,
born-red, substrate-gate-holding artifacts that flipped one `docs/design/README.md`
index row from `planned` to a link. This card mirrors their shape but sits one step
downstream: instead of adding a design doc it reconciles the agenda that gathers
their open-questions, now that all three are on `main`. The recurring planning-series
theme — the docs mostly ARM what already exists rather than inventing machinery —
carries into R's correction here: the resilience "gap" is not missing backoff but an
unhardened delivery boundary over machinery that already ships.

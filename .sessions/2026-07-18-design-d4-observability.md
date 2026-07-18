# 2026-07-18 — D4 observability-surface design doc (+ planning-mode design index)

> **Status:** `complete`

- **📊 Model:** opus-4.8 · medium · docs-only · D4 observability-surface design doc (born-red, holds substrate-gate)

## Scope

The completeness-reconciliation snapshot (`docs/status/completeness-table-2026-07-18.md`,
#525) concluded that the user-facing port surface is essentially exhausted and
recommended shifting the loop toward **PLANNING mode** — turning the D1–D6 forward
lanes into fuller design docs the owner reacts to and prioritizes. This slice is the
**first of that planning-mode design-doc series**: the **D4 observability-surface**
design doc, plus the series' shared home (a planning-index section on the existing
`docs/design/README.md`).

It is a docs-only planning artifact — no `sb/` code changes. The design doc is
grounded evidence-first in the ACTUAL observability surfaces read this session
(`sb/kernel/observability/{metrics,alerts,redaction,findings}.py`,
`sb/adapters/http/health.py`, `sb/spec/observability.py`, `sb/kernel/outbox/metrics.py`,
and the composition root `sb/app/main.py`), with `file:line` citations at HEAD `88f3c38`.

## Deliver

- `docs/design/D4-observability-surface.md` — the fuller design doc: Problem
  (grounded production-readiness gaps), Proposed design (Prometheus scrape wiring,
  a `/readyz` that also gates on outbox depth, structured-log coverage with a
  correlation ID threaded adapter→effect, redaction coverage on the log stream),
  Affected surfaces, Rough size (S/M/L + PR slicing), Open questions for the owner.
  `> **Status:** \`plan\`` badge (a valid docs-gate token).
- `docs/design/README.md` — a new **planning-mode design series** section + index
  table (D4/D5/D2/D1/D3/D6/B10/B8 with status), linking the D4 doc; the existing
  design-record index (game-sections, anchor-refresh-sweep) is preserved so nothing
  orphans. `> **Status:** \`reference\`` badge (unchanged).
- Reachability (docs-gate orphan check): one link from `docs/NEXT-TASKS.md` to the
  design index, near the completeness-snapshot link from #525.

## Verification

- `python3 bootstrap.py check --strict` → 0 exit-affecting findings (badges valid +
  all three docs reachable); the only red in CI is this card's own designed born-red
  hold on the substrate-gate until the card flips complete.
- No `sb/` or test code touched — docs-only; the functional CI gates ride green,
  substrate-gate is the expected sole hold.

## 💡 Session idea

The most load-bearing finding of the grounding pass is that superbot-next's
observability is **declared far ahead of where it is wired**: a 46-family metric
grammar (`sb/spec/observability.py`) + a 4-family outbox metric set
(`sb/kernel/outbox/metrics.py`) exist, but the composition root instantiates only
the default `METRICS` tuple (`sb/app/main.py:269`), so the outbox families — including
the `outbox_pending_age_seconds` relay-health alert shape — are never registered and
are silently swallowed by the guarded `_inc()` (`sb/kernel/outbox/relay.py:50-59`).
The design series should treat "close the declared-vs-wired gap" as the cheapest,
highest-signal first slice: it is a re-point plus a scrape target, not new subsystems.
A recurring theme across D1–D6 is the same shape — the grammar/spec leaves are richer
than the live wiring, so the planning docs are mostly about ARMING what exists, not
inventing.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-completeness-reconciliation.md` (#525), which produced
the 07-18 snapshot and whose explicit closing recommendation was to "shift the loop
toward PLANNING mode — turn D1–D6 into fuller design docs." This card is the direct
execution of that recommendation: it opens the planning-mode design-doc series with
D4 (the observability/metrics lane that snapshot filed under its D1–D6 forward row).
The snapshot's method — read BOTH sides in source, cite `file:line`, verdict only on
verified ground — is carried forward here: every gap the D4 doc names is grounded in
a citation from the real observability modules, not invented from the backlog label.

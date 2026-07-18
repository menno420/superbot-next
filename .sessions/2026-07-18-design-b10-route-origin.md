# 2026-07-18 — B10 panel-engine route-origin back-button design doc

> **Status:** `complete`

- **📊 Model:** opus-4.8 · medium · docs · B10 panel-engine route-origin back-button design doc (born-red, holds substrate-gate)

## Scope

The completeness-reconciliation snapshot (`docs/status/completeness-table-2026-07-18.md`,
#525) found the user-facing port surface essentially exhausted and recommended
shifting the loop toward **PLANNING mode** — turning the D1–D6 lanes and the
decision-sized backlog items into fuller design docs the owner reacts to and
prioritizes. This slice takes the reconciliation's **B10** item (marked OPEN and
"decision-sized") and turns it into a grounded design doc: the panel-engine
**route-origin signal** behind a dynamic back-button.

It is a docs-only planning artifact — no `sb/` code changes. The design is
grounded evidence-first in the ACTUAL panel engine + the oracle read this session
(`sb/spec/panels.py`, `sb/kernel/panels/{registry,engine,render,context}.py`,
`sb/kernel/interaction/request.py`, `sb/domain/role/panels.py`,
`sb/domain/server_management/panels.py`, and the oracle
`disbot/views/server_management/hub.py` + `disbot/views/navigation.py`), with
`file:line` citations at HEAD `b39a37f`.

## Deliver

- `docs/design/B10-panel-route-origin.md` — the fuller design doc: TL;DR,
  Problem (the oracle decides the back target from route origin; sb's nav row is
  origin-blind; the concrete role-hub "↩ Community" symptom), Proposed design
  (a `BACK_TO_ORIGIN` NavigationSpec mode + session-scoped `opened_from` captured
  on PanelRef navigation + a render resolver that falls back to `home_hub`),
  Affected surfaces, Rough size (M–L + slicing: engine-signal-first, then opt
  role.hub in), and Open questions for the owner (worth it? scope? depth?
  golden strategy for origin-dependent renders?). `> **Status:** \`plan\`` badge
  (a valid docs-gate token).
- `docs/design/README.md` — the B10 row in the planning-mode design series table
  flips from `planned` to a link `[B10](B10-panel-route-origin.md)`; every other
  row is preserved untouched (sibling design-doc PRs edit the same table).

## Verification

- `python3 bootstrap.py check --strict` → 0 exit-affecting findings (badges valid +
  the new doc reachable from the design index); the only red in CI is this card's
  own designed born-red hold on the substrate-gate until the card flips complete.
- No `sb/` or test code touched — docs-only; the functional CI gates ride green,
  substrate-gate is the expected sole hold.

## 💡 Session idea

The load-bearing finding of the grounding pass is that the port's nav grammar
**deliberately traded away** the very capability B10 asks for. The oracle
back-button is route-dependent because the OPENER injects it onto the child it
opens (`disbot/views/server_management/hub.py:96-113,169`) via a closure-backed
`parent_builder`/`BackTarget`. superbot-next's `NavigationSpec` docstring says it
"kills the closure-backed BackTarget/chain_back stacks" (`sb/spec/panels.py:174`)
to win restart-safety and byte-determinism — so the nav row became a pure
function of a panel's OWN static spec, with no opened-from input anywhere on the
wire (`PanelContext`/`ResolveRequest`/`PanelSession` all lack it). The design
therefore is not "add a button" but "reintroduce route-origin as a *serializable*
signal" — a session-scoped `opened_from` + a `BACK_TO_ORIGIN` rule that resolves
at click time with a `home_hub` fallback — keeping the determinism property the
port was built around. The real cost is not the engine change; it is the golden
harness gaining an **origin dimension** (the same panel now renders different
bytes by origin), which the doc flags as the key risk and a hard prerequisite of
opting any panel in.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-design-d4-observability.md` (#528), the first
planning-mode design-doc PR, which established the series' shape: read BOTH sides
in source, cite `file:line`, verdict only on verified ground, and open the doc as
a born-red card holding only the substrate-gate. This card carries that method
forward for B10 — every gap named (the oracle's opener-injected back-button, the
port's origin-blind nav row, the role-hub symptom) is grounded in a real citation
from the panel engine or the oracle, not inferred from the backlog label — and
reuses the exact born-red / card-flips-complete landing doctrine D4 proved out.

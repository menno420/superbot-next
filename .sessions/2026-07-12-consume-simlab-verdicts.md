# 2026-07-12 — sim-lab verdict consumption: V009/V010/V012/V013 dispositioned, AIP-02/03 fixed, check_doc_cites shipped

> **Status:** `in-progress`

- **📊 Model:** Fable · high · feature build + docs (Q-0194)

## Scope

Slice 4 of the owner's 2026-07-12 directive: consume the four unconsumed
sim-lab verdicts that `docs/review/sim-lab-review-2026-07-12.md` (#268)
found ("4 verdicts target this repo, 0 consumed"). Every claim
re-verified against source at HEAD before acting; per-item dispositions
recorded in the consumption section appended to
`docs/review/admin-surface-audit-2026-07-12.md`.

## Dispositions (summary — the doc section is the record)

- **V009 AIP-01** (dead Tools chooser): already fixed by D-0074 (the
  routing-matrix slice retired `chooser_scope_pending`) — recorded as
  consumed-by-convergence, no rework.
- **V009 AIP-02** (nav-less `ai.card` strands the operator): FIXED —
  `ai.card_nav`, the COMPONENT/MODAL-ingress card twin carrying the
  family `↩ AI home` back-route; command ingress stays on the bare
  `ai.card` (goldens/ai pins those replies at ZERO components —
  byte-parity preserved, zero golden re-cuts).
- **V009 AIP-03** (doubled `ai.` ack prefix): FIXED — acks/prompts print
  the bare settings_key (the one spelling the page already renders).
  Verified nuance: the doubled prefix was SHIPPED-OLD behavior
  (disbot/cogs/ai/schemas.py `name="ai_enabled"` + the
  `{subsystem}.{name}` ack format), so this is a deliberate, ledgered
  UX divergence on an unpinned surface — not a regression fix.
- **V009 19 display-only + 8 dead settings**: per-setting table in the
  doc section — KEEP/ledgered (byte-pinned parity surfaces whose engines
  are pending ports, or shipped-dead oracle artifacts); zero prune, zero
  golden movement, consistent with the admin-surface audit's zero-PRUNE
  ruling.
- **V010** (settle-once fence, approve): PARKED with written analysis —
  a real checker slice over the K7 op grammar, not a small fix;
  successor named in the doc section.
- **V012** (doc-cite checker, approve): BUILT — `tools/check_doc_cites.py`
  per the verdict's machine-readable winning spec + the ci.yml checker
  loop word; 0 red / 0 warn at HEAD.
- **V013** (oracle copy drift, reject-the-checker): the one-line fix is
  in flight in sibling PR #269 (recorded, not redone); the two optional
  same-class whitespace restores applied here (economy log_channel
  description + xp_cooldown hint back to the shipped two-space forms,
  oracle-verified).

## Evidence

- `python3 -m pytest tests/ -q` → 1744 passed, 2 skipped (pre-doc run);
  re-run at close-out.
- `python3 tools/run_golden_parity.py --gate` on real Postgres 16 →
  **GREEN, 412/412** goldens across 51 ported subsystems, with the
  AIP-02/03 changes in place.
- Full committed checker fleet green incl. the new `check_doc_cites`.

## ⟲ Previous-session review

Verified the sim-lab review doc's §4 re-verification table against
source before consuming: AIP-01/AIP-04 confirmed fixed (D-0074), AIP-02/
AIP-03 confirmed present, the 27 settings confirmed declaration-only.
One finding CORRECTED: the review (and V009) implied the AIP-03 doubled
prefix "did not exist in OLD" — search_code fragment reconstruction
shows OLD shipped the same doubled bytes; the fix stands on UX grounds,
recorded as a divergence rather than a parity restoration.

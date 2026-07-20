# Session — decision-audit pass (D2 DEFER + owner-agenda audit)

> **Status:** `in-progress`
>
> Born-red: this card is the sole FIRST commit (it holds the substrate-gate
> red); the docs/control edits land in the following commits; the
> `in-progress` → `complete` flip is the deliberate LAST commit.

- **📊 Model:** [[fill: model line at flip]]

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

[[fill: result at flip — files changed, D-ids, router flip, owner trim]]

## Verification

[[fill: pytest summary + bootstrap check at flip]]

## 💡 Session idea

[[fill: session idea at flip]]

## ⟲ Review

### previous-session review

[[fill: previous-session review at flip]]

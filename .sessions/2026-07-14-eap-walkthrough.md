# 2026-07-14 — ORDER 022 (b): EAP close-out walkthrough

> **Status:** `complete`

- **📊 Model:** fable-5 · ORDER 022 item (b) — the owner walkthrough doc

## Scope

Dispatched worker lane authoring and landing
`docs/eap-closeout-walkthrough-2026-07-14.md` per ORDER 022 (b)
(control/inbox.md:292-308): sections A (what shipped, PR-cited) ·
B (current state + verify commands) · C (OWNER ACTIONS checklist with
deep links, recommendations, VERIFY steps) · D (5-minute tour) ·
E (handoff). Plus one link line in `docs/current-state.md` § In flight
(the audit-link precedent at line 31). Docs-only — no code, no control
files touched.

Live facts carried from the coordinator dispatch (verified 2026-07-14
~11:27Z) plus this session's own reads at origin/main `7e3a488`
(#479 merged ~11:28Z — observed directly at branch cut, 11:30Z).

## Close-out

Landed as PR #480 (branch `claude/eap-walkthrough`): the walkthrough
doc + the one-line current-state link, session card born-red first.
Verification: `python3 -m pytest tests/ -q` **3115 passed, 15 skipped**
(twice, pre-push and pre-flip); `python3 bootstrap.py check --strict`
green but for the designed born-red HOLD (stamp finding fixed in
`67ca0a4` — the D-token had to be referenced as ledger-entry prose,
the audit's convention). All required gates green on head `67ca0a4`
at 11:45:00Z (golden-parity success 11:44:52Z); only the substrate-gate
card hold stayed red until this flip, as designed.

## 💡 Session idea

The stamp check taught the same lesson twice in one day (#440's
audit and this doc): any NEW doc that mentions a decision by its
D-NNNN token trips [stamp] unless it uses ledger-entry prose — but
the rule only surfaces at check time, after authoring. A one-line
"referencing decisions from a new doc? write `ledger entry NNNN`,
never the bare token" note in the docs-gate failure message (it
already names both files) would turn the fix from a re-derivation
into a copy-paste; today the finding text says "stamp each decision
at one home" without saying HOW a second doc may refer to it.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-14-order-022-verify-1-5.md`, PR #472.)
Exemplary verify-first work: it caught #464 as an empty vehicle by
reading the DIFF instead of the title, and its ⚑7 finding
(banner strings done-already via #393) held up — this session carries
that finding into the walkthrough's owner checklist instead of
re-asking the owner for work that's done. Its 💡 idea
(claims-terminal advisory) is real; the stale
`hygiene-claims-banners` claim it paid for is still a good checker
candidate. No slips found on re-read.

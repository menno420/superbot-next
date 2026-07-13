# 2026-07-13 — curation rework: ledger the leaderboard alias set deliberate (row 44)

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · curation rework lane · mandate: curation report
  row 44 (`docs/review/curation-report-2026-07-13.md` L948 + §Rework
  backlog "leaderboard alias fold" L1548), claim
  `control/claims/leaderboard-alias-fold.md` (PR #380), token
  `claude/rework-leaderboard-alias-fold`.

## Scope

The `leaderboard` CommandSpec (`sb/manifest/leaderboard.py:27-30`) carries
ELEVEN aliases the curation sweep flags as unexplained legacy duplicates.
Q-A03 (`docs/decisions.md:290`) is an owner-held default: legacy routes
stay callable — so the aliases stay VERBATIM; trimming would contradict an
owner ruling without an owner turn. The honest rework is regularization:
a DELIBERATE ALIAS SET ledger block in the manifest (row 73 / PR #379
precedent), plus a strengthened band4 set-pin test that fails toward
Q-A03 + the ledger on drift in either direction. Wire behavior unchanged,
zero golden churn, snapshot byte-stable (comments don't compile in —
verified via manifest_compile).

## What shipped

[[fill: close-out]]

## 💡 Session idea

[[fill: session idea]]

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-rework-server-management-name-pair.md`.)
[[fill: review]]

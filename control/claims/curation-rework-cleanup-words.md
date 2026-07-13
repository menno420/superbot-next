# Curation rework — cleanup panel wiring — `curation-rework-cleanup-words`

> **CLAIM (2026-07-13)** — curation-rework lane (SuperBot night run, ORDER
> 017 item 2; evidence: the curation review, chunk 3 — PR #327). This lane
> claims the "cleanup panel wiring" bundle so a concurrent fleet does not
> duplicate it. Earlier-at-HEAD claim wins on any collision.

**Scope.** The `cleanup.words` panel's four wireable buttons plus the
`cleanup.hub` logging nav: word_add / word_remove (button → modal → the live
`cleanup.word_add_op` / `word_remove_op` command-twin workflows, the
moderation.hub.warn modal-ingress precedent), scan_history (→ the live
`cleanup.history_scan` handler), word_refresh (REFRESH_PANEL nav, the
`cl_refresh` pattern), and the hub's 📝 Logging Status button (→
`panel:logging.hub`, its server-logging successor already landed).

**EXCLUDED.** server_management, mining, utility and btd6 panels — sibling
rework PRs own those. The words manager's live `Current Words` field read and
the anti-evasion toggle stay the word-mutation slice's (golden-pinned
literals; goldens/cleanup/sweep_wordmenu).

- `curation-rework-cleanup-words` · **curation rework — wire cleanup.words add/remove/scan/refresh buttons + cleanup.hub logging nav to live workflows** — retires 5 pending terminals whose live targets already shipped · sb/domain/cleanup/, tests/ · 2026-07-13

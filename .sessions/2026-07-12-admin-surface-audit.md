# 2026-07-12 — Admin-surface audit consolidation (owner directive slice 2)

> **Status:** `complete`

- **📊 Model:** fable-5 · high · docs/audit (Q-0194)

## Scope

Slice 2 of the owner's 2026-07-12 core-admin-function-audit directive:
consolidate the four parallel read-only audit passes (AI settings
verification, moderation/settings/setup, tickets/xp/channel/proof-channel,
diagnostics/economy/AI routing) into one repo document and ship it
merged-on-green. Docs/control-only; no domain code touched. The one
FIX-now item the audits produced (`!givexp` bare-ID misparse) is being
shipped by a **parallel slice** of the same directive — cross-referenced,
not duplicated.

## What shipped

1. **`docs/review/admin-surface-audit-2026-07-12.md`** — audited HEAD
   `764a393` (#260); one master verdict table (every row file:line-cited,
   verdicts OK/FIX/PARK/PRUNE), the 3-item FIX list
   (`!givexp` misparse → parallel slice; `post_action_cleanup(+_limit)`
   zero consumers; `public_log_actions`/`public_log` declared-editable
   but ignored by server_logging), the headline PARK/ledgered gaps
   (D-0049 unarmed live ports incl. GuildModerationActions /
   ChannelStateActions / ChannelPermActions / ws-latency / guild
   directory; Settings Manager + setup wizard pending-terminal shells;
   Cog Manager stub; ⚑ live-misleading capture-literal diagnostics;
   SETUP_ADVISOR_PROVIDER still open at control/status.md:200), the AI
   settings verification result (26 PanelSpecs, 114/114 refs, 0 pending
   terminals, byte-pinned layout — rebuild NOT needed; 5 modernization
   candidates PARK), the ensure-only allowlist correction (**42 rows =
   mining 26 + fishing 15 + role 1**, correcting the #160-era 45-count),
   and the explicit zero-PRUNE statement (no orphaned custom_ids
   anywhere). Indexed in `docs/review/README.md`.
2. **control/status.md heartbeat** — `updated:` stamp, the audit fold in
   `last-shipped:` (band position, this doc, gate 412/412 across 51,
   blockers unchanged), prior fold kept verbatim.
3. This session card + its telemetry row (Q-0194, family-level model
   name only).

## Verification

- Load-bearing citations spot-re-verified against source at
  `dd76427` before writing (xp ops.py:58-88 misparse mechanics,
  server_logging/service.py:365-382 hardcoded default,
  `rg post_action_cleanup` zero consumers, the 42-row allowlist counted
  from tests/unit/invariants/test_composition_parity.py:35-78, the 26
  `_SPECS` entries, check_database literal handlers.py:182-200, the
  five unarmed ports absent from sb/app/main.py and present only in
  sb/adapters/parity/boot.py:493/562/598). One correction folded in:
  the moderation-actions arming cite is `boot.py:493-494`
  (`ParityModerationActions`, the GuildModerationActions capture twin).
- `python3 -m pytest` green locally before push (summary in the PR).
- Merged on green (6 required checks; `report` red-by-design).

## 💡 Session idea

The audits disagreed on verdict grammar (the diagnostics pass graded
live-misleading capture literals FIX; the directive rules them
PARK/ledgered). A one-line verdict rubric in docs/review/README.md
(FIX = no ledger entry found; PARK = ledgered, however ugly) would keep
future multi-worker audits mergeable without a re-grade pass.

## ⟲ Previous-session review

The program-review session (#256 lineage, card
`.sessions/2026-07-12-program-review.md`) set the pattern this doc
reuses: provenance header with audited SHA + moved-HEAD flag, file:line
on every load-bearing claim, plain-language master summary. Its Top-10
item 5 (live effect adapters unarmed) is confirmed unchanged by this
audit and now carries the per-port cite list.

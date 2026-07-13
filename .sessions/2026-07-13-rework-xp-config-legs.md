# 2026-07-13 — curation rework backlog slice 1: xp.config mutation legs

> **Status:** `complete`

- **📊 Model:** Claude (Fable family) · curation-report REWORK backlog,
  slice 1 · mandate: docs/review/curation-report-2026-07-13.md §Rework
  (c) Backlog — "**xp.config ×4** — port the xp config mutation legs
  (xp_range / xp_cooldown / xp_levelup_channel / xp_import) in
  sb/domain/xp — oracle xpconfig legs are live-wired; one contained
  slice."

## Scope

Arm the four `xp.config` panel pending-terminal buttons onto their live
targets (the cleanup-words / moderation.hub.warn modal-ingress
precedent, PR #333 lineage):

1. `xp_range` — button → G-10 modal (oracle `_XpRangeModal` verbatim:
   Min/Max fields, "❌ Both values must be integers." / "❌ Max must be
   ≥ min.") → two audited `settings.set_scalar` writes (xp_min, xp_max).
2. `xp_cooldown` — button → modal (oracle `_XpCooldownModal`:
   "❌ Cooldown must be an integer.") → `settings.set_scalar`
   (xp_cooldown).
3. `xp_levelup_channel` — button → modal (oracle `_XpChannelModal`:
   empty clears, numeric ID sets, "❌ Channel must be empty (to clear)
   or a numeric Discord channel ID.") → `settings.bind` /
   `settings.unbind` on the `xp.announce_channel` binding (the P0-3
   pointer lane; the server_logging bind precedent).
4. `xp_import` — button → modal ingress collecting source / channel /
   limit, delegating to the LIVE `!xpimport` front-door walk (the
   utility poll/remind backlog pattern). The select-driven
   XpImportSetupView picker and the preview/apply panel stay the
   import-preview slice's — the scan's honest BLOCKED boundaries are
   unchanged.

Oracle: menno420/superbot@cdb2680 disbot/views/xp/modals.py (fetched at
session time — copy mirrored verbatim where cited).

## What shipped

All four legs landed — none dropped (each verified still-pending at
HEAD `d304ea3`; no claim/PR collision on sb/domain/xp — collision check
covered control/claims/ at HEAD, all 12 open PRs, and the
refs/heads/claude/* namespace):

- `sb/domain/xp/panels.py` — four G-10 ModalSpecs (`xp.range_form` /
  `cooldown_form` / `channel_form` / `import_form`, oracle-verbatim
  titles + field labels), the 4 actions rewired `defer_mode=MODAL` →
  `HandlerRef(xp.config_*_submit / xp.import_setup_submit)`; the
  `_register_pending` block retired.
- `sb/domain/xp/handlers.py` — the 4 submit handlers (oracle validation
  copy verbatim; `_write_xp_scalar` bounds-checks against the declared
  SettingSpec bounds then rides `settings.set_scalar`; the channel leg
  rides `settings.bind`/`unbind`; the import leg builds the front-door
  argv and delegates); `!xpimport`'s walk extracted to `_xpimport_walk`
  (shared, byte-identical behavior).
- `tests/unit/band4/test_band4_xp.py` — wiring-shape pin (4× modal
  ingress + registered submits), retired-refs burn-down pin,
  validation-copy + write-param behavior tests (recorded engine:
  set_scalar keys/values, bind/unbind params), import-delegation pin.
- `manifest.snapshot.json` recompiled (`manifest_compile --write`);
  `compat/compat-frozen.json` regenerated (+4 modal-id custom-id roots).
- Verify: `python3 -m pytest tests/ -q` → 2109 passed, 13 skipped;
  `bootstrap.py check --strict` → exit 0 (only the designed born-red
  hold pre-flip); check_namespace / check_compat_frozen /
  check_symbol_shadowing / check_no_skip / check_config_usage /
  check_parity_depth / check_escape_hatches all OK. No goldens touched
  (no golden clicks these buttons; handler refs are not wire bytes).

Flagged decisions (PL-001, one line each): bounds refusal copy
("❌ {key} must be between {lo} and {hi}.") is minted — the oracle
surfaced its pipeline validator's exception text, which the port's
caller-side check replaces; the import button rides a MODAL ingress
over the live `!xpimport` walk rather than porting the select-driven
picker — the picker + preview/apply half is the import-preview slice's
named scope, and the report's own vocabulary for this rework class
(utility poll/remind, btd6 ctteam) is modal-ingress-over-live-op.

## 💡 Session idea

The report's backlog golden-mint items (`pay`, farm, rps quickplay) are
all parked behind the parity corpus count-pin while mining WP PRs
#312/#317/#335 hold parity.yml open — when those merge, one sibling
lane could batch all three mints in a single corpus-count bump instead
of three rebase races over the same pin line.

## ⟲ Previous-session review

Previous card (`.sessions/2026-07-13-curation-rework-cleanup-words.md`,
PR #333): clean, and its 💡 (make `git worktree add` the first step of
every parallel lane) held — this session ran in an isolated worktree
from step 0 and hit zero shared-checkout races. Its modal-ingress
pattern transferred verbatim; the only friction it didn't warn about:
`dataclasses.replace` on the request means handler tests need a
dataclass ResolveRequest twin, not a SimpleNamespace.

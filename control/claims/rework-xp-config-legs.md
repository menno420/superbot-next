# Curation rework backlog — xp.config mutation legs — `rework-xp-config-legs`

> **CLAIM (2026-07-13T02:58:42Z)** — curation-report REWORK backlog slice 1
> (docs/review/curation-report-2026-07-13.md §Rework (c) Backlog:
> "**xp.config ×4** — port the xp config mutation legs (xp_range /
> xp_cooldown / xp_levelup_channel / xp_import) in sb/domain/xp — oracle
> xpconfig legs are live-wired; one contained slice."). Earlier-at-HEAD
> claim wins on any collision.

**Scope.** The four `xp.config` panel pending-terminal buttons → live
targets: xp_range / xp_cooldown (G-10 modals → audited
`settings.set_scalar`), xp_levelup_channel (modal → `settings.bind` /
`settings.unbind` on `xp.announce_channel`), xp_import (modal ingress →
the live `!xpimport` front-door walk). EXCLUDED: the select-driven
import picker + preview/apply panel (import-preview slice), the settings
hub mutation surface (settings-mutation slice, PARKed), all parity
goldens.

- `rework-xp-config-legs` · **curation rework backlog slice 1 — arm the 4 xp.config buttons (range/cooldown/channel/import) onto live settings ops + the xpimport front door** — branch `claude/rework-xp-config-legs` · sb/domain/xp/, tests/unit/band4/, manifest.snapshot.json, compat/compat-frozen.json · 2026-07-13

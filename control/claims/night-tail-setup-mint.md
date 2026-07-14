# Claim — night-tail: mint disposition posture + setup deferrals

> ⚑ Self-initiated (coordinator-dispatched night-tail; ORDER 019's listed
> items are complete). Three slices, one PR each. Excludes: parity/cases
> WP files, parity/parity.yml count pins, parity/goldens/mining/ — the
> WP-stack lane is active there.

- `claude/night-tail-1` · **tools/mint_golden.py disposition posture fix** — verify-first: post-#416 `--write` applies replay dispositions at mint time, stripping ratchet-counted rows (audit_log/event_outbox/economy_balances) from minted goldens; fix so mints carry the canonical posture (reconcile with #449's canonical re-mints) + regression pin · area: tools/mint_golden.py, new unit test; zero existing golden bytes · 2026-07-14
- `claude/night-tail-2` · **setup: on-guild-join launcher panel port** — port the oracle's on-guild-join launcher panel onto the edit_anchored_panel seam (#437); oracle read via GitHub API pinned @ bbc524e (local oracle clone = ledgered wall) · area: sb/domain/setup/, sb/manifest/, tests/unit/setup_band/ · 2026-07-14
- `claude/night-tail-3` · **setup: hub per-section failure notice** — the small shared catch seam the SectionRecoveryView lane (#444) sized as its own slice · area: sb/domain/setup/, tests/unit/setup_band/ · 2026-07-14

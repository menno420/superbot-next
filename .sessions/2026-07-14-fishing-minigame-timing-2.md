# 2026-07-14 — fishing: minigame timing rung slice 2 — live bite edits + full enforcement (D-0043)

> **Status:** `in-progress`

- **📊 Model:** Claude (Fable family)

## Scope

Claimed lane (`control/claims/fishing-minigame-timing.md`, slice-2 leg;
branch `claude/fishing-minigame-2`, follows PR #460): the push-edit
half of the docs/decisions.md fishing-minigame timing rung —

- **Kernel session push-edit seam**: `PanelSession` grows
  `channel_id`; a new engine entrypoint renders a live session view
  onto its ORIGINAL minted component ids and presents through the
  `_message_editor` port (no ResolveRequest) — uninstalled editor ⇒
  `EDIT_UNAVAILABLE` no-op (headless/parity posture).
- **One-shot timer seam**: an in-process asyncio one-shot timer
  utility (kernel band) — cancel-safe, exception-contained,
  process-local (ADR-002 restart-loss posture).
- **Domain wiring** (`sb/domain/fishing/service.py`): fake-out nibble
  / 🐟 BITE! / unprompted got-away edits armed at cast park; fight
  inter-round re-arm beats; timers cancelled wherever a pending cast
  resolves or is swept.
- **Enforcement flip**: late reel (now > bite_at + window) → the
  oracle got-away terminal (+ trophy escape clue); fight tap windows
  enforced per round; the slice-1 "late = in-time" posture and its
  ledger notes removed.
- **Goldens**: retune the 3 reel-write goldens' click steps with
  in-window `advance_s`; verify the 4 slice-1 timing cases still land
  their branches; re-mint via `tools/mint_golden.py` only.
- **Decision entry** documenting the sanctioned real-time lane; units
  for the timer seam, the push seam, and the enforcement flip.

Untouched by design: control/status.md, control/inbox.md,
control/outbox*, mining domain files, WP parity branch files.

## Verification

(to be filled at close-out)

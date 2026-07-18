# 2026-07-18 — harden: fail-close the workflow banned-I/O fence when handler source is un-inspectable

> **Status:** `in-progress`
>
> Born-red first commit (per `.sessions/README.md`) — this HOLD keeps the PR red
> via substrate-gate until the deliberate LAST commit flips it to `complete`,
> releasing the born-red HOLD so the server-side lander can merge on green.

- **📊 Model:** Opus family · small · additive hardening slice
- **Born:** 2026-07-18 (born-red first commit)

## Scope

Close a fail-open hole in `check_atomic_db_only` (the external-conn fence, spec
07 §3.6) in `sb/kernel/workflow/compile.py`. The fence scans a DB-leg handler's
source for banned I/O tokens via `inspect.getsource`. When the source could not
be read it swallowed the exception and fell back to an empty string — so an
**un-inspectable DB-leg handler silently PASSED the fence** (fail-open). This
slice makes it **fail-CLOSED**: an un-inspectable handler now records a problem
so the banned-I/O fence can never be silently bypassed.

Branch `claude/harden-workflow-io-fence` off origin/main `1893d32`. This card is
the first commit (born red); the compile.py change + test follow in a second
commit.

## Files touched

- `sb/kernel/workflow/compile.py` — `check_atomic_db_only`: the
  `except: source = ""` fail-open swap replaced with a recorded problem +
  `continue` (fail-closed), matching the function's existing `problems.append`
  violation shape.
- `tests/unit/workflow/test_spec_and_fences.py` — added a fail-closed test: a
  DB leg whose handler is built dynamically (so `inspect.getsource` raises)
  now records a problem naming the un-inspectable source; the existing
  positive/negative cases stay green.

## Verification

- `python3 -m pytest tests/unit/workflow/ -q`
- `python3 -m pytest tests/unit/ -q`

## Why born-red

Card is intentionally `in-progress` (born-red) so substrate-gate holds the PR
red. The owner flips it to `complete` as the deliberate LAST commit once CI
confirms the `gate` job is green.

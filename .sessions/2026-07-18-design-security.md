# 2026-07-18 — Security design doc: secret rotation + startup fail-closed + least-privilege

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · medium · docs · S security design doc (secret rotation + startup fail-closed + least-privilege; born-red, holds substrate-gate)

## Scope

A NEW production-readiness design topic beyond the D1–D6 planning lanes: a
grounded **security** design doc covering three gaps the credential/config
kernel exposes today — (1) no documented **zero-downtime rotation** for the
`WORKER_ENV` secrets a leak forces an emergency swap of
(`DISCORD_BOT_TOKEN_PRODUCTION`, `DATABASE_URL`); (2) whether startup **fails
closed** on a missing/malformed required secret, or half-boots; (3) no recorded
**least-privilege review** of the bot's Discord intents + the DB connect role.

It is a docs-only planning artifact — no `sb/` code changes. The design is
grounded evidence-first in the ACTUAL credential/config kernel + boot path read
this session (`sb/kernel/credentials/{rotation,cadence}.py`,
`sb/kernel/config/__init__.py`, `sb/spec/{config,credentials}.py`,
`sb/adapters/discord/gateway.py`, `sb/app/main.py`, and the existing
`docs/operations/credential-lifecycle.md`), with `file:line` citations at HEAD
`cae15f8`.

## Deliver

- `docs/design/S-security-rotation-and-least-privilege.md` — the fuller design
  doc mirroring D4: TL;DR, Problem (S1 rotation seam exists but is CUT-1
  un-wired and the two highest-blast worker secrets have no cadence path; S2
  preflight DOES fail closed on absent required FAIL_FAST secrets but an opaque
  SECRET passes coercion unvalidated and only trips late at gateway connect; S3
  `Intents.default()` is a broad bundle, the DB role is the DSN's embedded
  connect user with migration DDL rights), Proposed design (a documented
  drain-and-reboot rotation runbook riding the existing phase ledger + a
  RotationProvider install; a preflight `SECRET`-shape sanity check that
  fails closed early; a least-privilege audit trimming intents to the consumed
  set + splitting a DDL migration role from a DML runtime role), Affected
  surfaces, Rough size (S/M per component with slicing — fail-closed guard
  first), and Open questions for the owner. `> **Status:** `plan`` badge.
- `docs/design/README.md` — a new `## Beyond D1–D6 — production-readiness
  tracks` section (created if absent; appended to if a sibling made it) with a
  `[Security](S-security-rotation-and-least-privilege.md)` row. Every existing
  D-series / planning-mode row is preserved untouched (sibling design-doc PRs
  edit the same file).

## Verification

- `python3 bootstrap.py check --strict` → 0 exit-affecting findings (badges
  valid + the new doc reachable from the design index); the only red in CI is
  this card's own designed born-red hold on the substrate-gate until the card
  flips complete.
- No `sb/` or test code touched — docs-only; the functional CI gates ride
  green, substrate-gate is the expected sole hold.
- Secret VALUES never appear anywhere in the doc — env-var NAMES only.

## 💡 Session idea

The load-bearing finding of the grounding pass is that the security machinery is
**built but deliberately un-armed**, so the real gaps are seams and runbooks,
not missing subsystems. Rotation has a full resumable phase ledger
(`sb/kernel/credentials/rotation.py`) whose `RotationProvider` port is
un-installed by design — an un-wired rotation FAILs loudly
(`rotation.py:135-148`) — AND the two secrets a leak would force an emergency
swap of are exactly the ones the cadence detector never arms:
`discord_prod_bot_token` is `ON_COMPROMISE` (no cadence) and `prod_dsn` is
`MANAGED`, both skipped by `rotation_due` (`cadence.py:59-61`). So "zero-downtime
rotation" is not a hot-swap the code lacks a hook for; it is a **drain-and-reboot
runbook** the phase ledger already makes crash-safe — `WORKER_ENV` swap = var
change = redeploy = restart (Q-0193), and `main.py` reads the frozen `Config`
token exactly once at connect (`main.py:598`), so no live re-read seam exists to
hot-swap into anyway. On fail-closed the honest verdict is that preflight
**already** refuses boot on an absent required FAIL_FAST secret
(`config/__init__.py:187-189`, `main.py:218-221`), so the zombie-half-boot risk
is smaller than feared; the residual gap is that a *malformed* opaque `SECRET`
passes `_coerce` unchanged (`config/__init__.py:118-122`) and surfaces late at
gateway connect rather than early at preflight. Least-privilege is the widest-open
of the three: `Intents.default()` (`gateway.py:54`) turns on every non-privileged
gateway intent regardless of which feeds `main.py` actually arms, and the DB
connect role is whatever the `DATABASE_URL` DSN embeds — the same role that runs
migrations, so it holds DDL the steady-state worker never needs.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-design-b10-route-origin.md` (#530), a
planning-mode design-doc PR, which reaffirmed the series shape D4 established:
read the real code on BOTH sides, cite `file:line`, verdict only on verified
ground, and open the doc as a born-red card holding only the substrate-gate.
This card carries that method to a NEW production-readiness topic (security)
outside the D1–D6 lanes — every gap named is grounded in a real citation from
the credential/config kernel or the boot path, not inferred from a backlog
label — and reuses the exact born-red / card-flips-complete landing doctrine
the design series proved out.

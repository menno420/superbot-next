---
state: captured
origin: consumer:menno420/superbot
shipped_pr: null
shipped_repo: null
merged_date: null
outcome: open
---

# Port the small four: utility, general, four_twenty, paragon (2026-07-10)

> **Status:** `ideas`
>
> **State:** captured (gen-2 night-prep seed by the grand-review session).
> **Origin:** the verified old-vs-new gap map, superbot
> `docs/eap/gen1-grand-review-2026-07-09.md` §2.

**One line:** four whole subsystems verified missing AND verified decision-free — port
each as its own band-6-style PR (manifest + domain + tests): `general` (8 delight
commands, 371 oracle lines), `four_twenty` (1 command, 256 lines), `paragon` (the math
already lives in `sb/domain/btd6/paragon_math.py` — wiring only), `utility` (15 commands,
725 lines; `remind` maps onto the K9 due-queue).

**Why now:** parity rows for all four already exist in `parity/parity.yml` (the plan
intends them); none needs an owner ruling; each is a clean overnight-sized lane that
doesn't collide with band-5 live-drive. Suggested order: four_twenty → general → paragon
→ utility (smallest first, walking-skeleton spirit).

**Not in scope:** `starboard` (blocked on a reaction adapter — separate idea),
`ticket` (medium, fine as a follow-on), `ux_lab`/`hermes` (product calls, route to the
owner).

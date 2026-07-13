# Energy-system port — scoping doc (scope-only, NO implementation)

> **Status:** `plan`

> Decision ids are cited by concept here, not by raw ledger id, to keep one
> ledger home (the repo's stamp-discipline / decision-provenance rule). The
> deep-game-ports go/no-go lives in the ledger + `control/status.md`
> ⚑ needs-owner #1; energy is the last un-ported mining deep-system it gates.

Scoped 2026-07-12. Oracle: `menno420/superbot` @ `87bbe1dbf0c504d1ef1fc9db466224303f16afba` (read-only).
Target: `menno420/superbot-next` @ `main` HEAD `33d307389b979789f88c1ffc515693896f606ee5` (verified via ls-remote; fresh clone at same SHA).
Posture: faithful port — oracle-verbatim constants/copy, goldens via canonical harness, no product decisions.

---

## STEP 0 — COLLISION CHECK

### Deep-mining WRITE-PARITY (WP) lane — active claims
- Claim file: `control/claims/mining-write-parity-lane.md` (branch `mining-write-parity-lane`).
- Six slices WP-1..WP-6. WP-1 delivered (#306, merged). Open PRs in flight:
  - **#312** `mining-write-parity-wp2` — vault write goldens (base main).
  - **#317** `mining-write-parity-wp3` — depth/world/wear + workshop goldens; **STACKED on WP-2**; base `mining-write-parity-wp2`. **Retires the `mining_player_state` depth exemption and ratchets mining `{events:4,tables:13}→{5,16}`.**
- The WP lane touches only `parity/cases/`, `parity/goldens/mining/`, `parity/parity.yml` (WP-2/3/4 are pure capture) plus `sb/domain/mining/` for WP-5/6 (skill/build PORTS).

### The explicit exclusion (the energy lane is pre-carved)
`control/claims/mining-write-parity-lane.md` lines 23-26 (quoted; the ledger decision-id elided per stamp discipline):
> **EXCLUDED — cook / use.** The `!cook` / `!use` argful writes depend on the un-ported mining energy/consumable system (a **separate lane**) and stay honest deep-game-ports pending terminals; they register no covered store, so there is NO exemption to retire. This lane does NOT touch them.

So the WP lane has **explicitly ceded** cook/use + the energy system to a "separate lane." No energy claim file exists yet (`grep -rniE 'energy' control/` returns only this exclusion note, status.md's slice-4 line, and the moderation-unrelated hits).

### Collision verdict
- **Claim files / capture files: CLEAR.** The WP lane's mutation captures never touch cook/use or an energy store; no energy claim exists; the two do not overlap on any claim file (0% by the one-file-per-claim invariant).
- **⚠ Shared-table contention on `mining_player_state`: PARTIAL RISK — only if dig is wired (see the owner decision).** The oracle stores energy on `mining_player_state` (`energy`, `energy_updated_at` columns), the SAME table WP-3 (#317, OPEN) is mid-flight retiring the depth exemption on and ratcheting. If the energy lane wires energy-spend into `!fastmine` (oracle behavior), it ADDS an energy-column write to `sweep_fastmine`'s db_delta and to the `mining_player_state` contract WP-3 is actively re-freezing → a real db_delta/ratchet collision, even though the claim files don't overlap. If the energy lane wires **only cook/use** (which write energy but not via the mine leg) the contention is limited to the cook/use argful goldens, which are net-new and WP-excluded.
- **Proposed claim file:** `control/claims/mining-energy-consumable-port.md` (matches the WP lane's "separate lane" language and the `<branch-or-scope>.md` convention in `control/claims/README.md`). Suggested bullet token: `mining-energy-consumable-port`.

### Open PRs that could collide
| PR | Branch | Touches | Collision |
|----|--------|---------|-----------|
| #317 | mining-write-parity-wp3 | `mining_player_state` db_delta + mining ratchet | **YES if dig wired** — shared table + ratchet |
| #312 | mining-write-parity-wp2 | `mining_vault`/`mining_player_state.vault_level` | Indirect (same table, different column) |
| #313 | claude/fishing-slice1-forecast-sail | fishing venue, migration 0048 | Migration-number sequencing only |
| #296 | (parked) Mining slice-4 | forge/repair/quickcraft/**cook/use** wiring | **cook/use route landing** — verify #296's cook/use is the BLOCKED-terminal version (it is: service.py:894/911 ship the pending copy) |
| #318 | local-env-hygiene | docs/tools only | None |

---

## STEP 1 — ORACLE ENERGY SYSTEM MAP

### Domain core — `disbot/utils/mining/energy.py` (@ 87bbe1d)
Pure functions, no DB/Discord. **Constants (VERBATIM):**
```
MAX_ENERGY   = 60
DIG_COST     = 1
REGEN_SECONDS = 10          # +1 energy / 10s = 360/active-hour = the sim-pinned dig throttle
RESTORE_VALUES = {"ration": 25, "energy drink": 50, "cooked fish": 30}
```
`@dataclass(frozen=True) EnergyState(current:int, updated_at:int)`.

Functions (signatures verbatim):
- `settle(state, now, *, max_energy=MAX_ENERGY, regen_seconds=REGEN_SECONDS)` — lazy on-access regen: `if current>=max: return (max, now)`; `elapsed=max(0,now-updated_at)`; `gained=elapsed//regen_seconds`; advances `updated_at` by whole intervals only (partial regen never evaporates).
- `can_dig(state, now, *, cost=DIG_COST, ...)` → `settle(...).current >= cost`.
- `spend(state, now, *, cost=DIG_COST, ...)` → settle then `EnergyState(max(0, s.current-cost), s.updated_at)`.
- `restore(state, now, amount, *, ...)` → settle then `EnergyState(min(max, s.current+amount), s.updated_at)`.
- `seconds_until(state, now, target, *, ...)` → passive-regen seconds until `target`.
- `restore_value(item)` → `RESTORE_VALUES.get(item.strip().lower())` or `None`.
- `bar(current, max_energy=MAX_ENERGY, *, width=10)` → `f"⚡ {current}/{max_energy} [{'▰'*filled}{'▱'*(width-filled)}]"`, `filled=round(width*current/max_energy)`.

**Design intent (session `.sessions/2026-06-22-mining-energy-rebalance.md`):** energy is the owner's chosen frequency brake *instead of* a per-dig cooldown (2026-06-22). "Decisions made alone (owner should sanity-check): MAX_ENERGY=60, DIG_COST=1, regen +1/10s, ration +25 / energy drink +50, market prices 20/40." Shipped via oracle migration **086**.

### Regen mechanics
On-access lazy regen (stored value + timestamp, **never a background ticker** — ADR-001/002). Missing row → `(0,0)` → settles to full bar (a huge elapsed-from-epoch clamps to cap), so every fresh/legacy player starts full. Identical math to the already-ported fishing energy (`sb/domain/fishing/energy.py`) — the oracle kept two copies by a deliberate rule-of-three note; the ONLY differences are the constants (`DIG_COST=1` vs fishing `CAST_COST=2`; `REGEN_SECONDS=10` vs fishing `30`) and the `restore`/`restore_value`/`seconds_until` additions (fishing has no food refill).

### Consumption / production legs — `disbot/services/mining_workflow.py` (@ 87bbe1d)
1. **DIG (`mining_workflow.mine`)** — driven by `!fastmine` AND the `!mine` grid navigator (`mining_cog.py fastmine` → `mining_workflow.mine(author.id, guild.id)`). Gate + spend:
   ```
   e_state = energy.EnergyState(*await db.get_energy(suid, guild_id))
   if not energy.can_dig(e_state, now):
       wait = energy.seconds_until(e_state, now, energy.DIG_COST)
       # refuse with the out-of-energy hint (verbatim):
       "⚡ You're out of energy — rest a moment (~{wait}s until your next dig) or eat a **ration** / **energy drink** (`!use ration`)."
   spent = energy.spend(e_state, now)                       # DIG_COST=1
   await db.set_energy(suid, guild_id, spent.current, spent.updated_at, conn=conn)
   ```
   **At 0 energy: dig is REFUSED** (returns the hint, no loot, no XP). The fastmine cog reply itself carries **no energy bar** — just `{mention} mined **{amount}x {found}** in {position}!` + wear/xp/pack notes.
2. **COOK (`mining_workflow.cook(user, guild, fish, qty=1)`)** — campfire-gated fish→"cooked fish":
   - gate: `if not structures.cooking_unlocked(built.get(CAMPFIRE,0)): "You need a 🔥 **Campfire** to cook — build one with `!build campfire`."`
   - success (verbatim): `f"🔥 You cook **{qty}× {fish}** into **{qty}× cooked fish** (+{gain} ⚡ each when eaten — `!use cooked fish`)."` where `gain = RESTORE_VALUES["cooked fish"] = 30`. Both legs (raw-fish debit + cooked-fish grant) in ONE txn. Does NOT itself refill energy — it MINTS the consumable.
3. **USE (`mining_workflow.use_item(user, guild, item)`)** — consumable/food:
   ```
   restore = energy.restore_value(item)
   if restore is not None:                                  # it's food
       if energy.settle(e_state, now).current >= energy.MAX_ENERGY:
           return "Your energy is already full — save it for later."
       restored = energy.restore(e_state, now, restore)
       # ONE txn: debit item -1 + set_energy
       return f"You consume **{item}** and recover energy ({energy.bar(restored.current)})."
   ```
   Non-food flavour (verbatim): torch `"You light a torch and peer into the darkness..."`; dynamite `"You ignite dynamite and blow a new path in the mine!"`; generic `f"You used **{item}**, but nothing special happened."`

### Persistence shape — `disbot/utils/db/games/mining_player_state.py` (@ 87bbe1d)
Energy lives on the **existing `mining_player_state` table** (NOT a separate table — contrast fishing, which uses a dedicated `fishing_energy` table). Columns: `user_id TEXT, guild_id INT, depth, max_depth, vault_level, last_broken_item, equipped_title, **energy INTEGER, energy_updated_at INTEGER**, updated_at TIMESTAMP`.
```python
async def get_energy(user_id, guild_id, *, conn=None) -> tuple[int,int]:   # missing row → (0,0)
async def set_energy(user_id, guild_id, energy, updated_at, *, conn=None) -> None:
    # INSERT ... (user_id,guild_id,energy,energy_updated_at) VALUES ($1,$2,$3,$4)
    # ON CONFLICT (user_id,guild_id) DO UPDATE SET energy=$3, energy_updated_at=$4, updated_at=now()
```
No advisory lock on the energy read/write (energy is game pacing, not coins — non-money lane). Oracle migration **086** added the columns.

### Market coupling — `disbot/utils/mining/market.py` / `items.py`
Food/boosters are buyable coin sinks: `"ration": 20, "energy drink": 40` (market prices; restore values 25/50). "cooked fish" is player-minted via `!cook`, not bought.

### Dependent commands (oracle file:line ↔ next file:line)
| Command | Oracle | Reads/writes energy | Next-side (superbot-next) | Next status |
|---------|--------|---------------------|---------------------------|-------------|
| `!fastmine` | `mining_cog.py::fastmine` → `mining_workflow.mine` | **spend + gate** | `sb/domain/mining/service.py:207` `fastmine_route` → `ops.py:84` `record_mine` | **LIVE, golden `sweep_fastmine.json`, NO energy** |
| `!mine` (grid) | `mining_cog.py::mine` → `mining_workflow.mine` | **spend + gate** | `sb/domain/mining/service.py:198` `mine_route` | BLOCKED terminal (grid nav RAISED in capture-world; pins bot1 generic copy) |
| `!cook` | `mining_cog.py::cook` → `mining_workflow.cook` | mints cooked fish | `sb/domain/mining/service.py:894` `cook_route` | **PENDING terminal (BLOCKED argful)** |
| `!use` | `mining_cog.py::use` → `mining_workflow.use_item` | **restore + debit** | `sb/domain/mining/service.py:911` `use_route` | **PENDING terminal (BLOCKED argful)** |

---

## STEP 2 — NEXT-SIDE LANDING SURFACE

### The template already exists — fishing energy is ported
`sb/domain/fishing/energy.py` is the byte-for-byte precedent for the mining energy port. Its own docstring (lines 1-14): *"the regen math mirrors the shipped mining energy module — the oracle's own rule-of-three note kept the two copies separate."* The mining port = fishing port with the mining constants + the three extra functions (`restore`, `restore_value`, `seconds_until`).

**Model the port on the fishing subsystem, seam-for-seam:**
- **Domain core:** `sb/domain/fishing/energy.py` → new `sb/domain/mining/energy.py` (pure, verbatim constants).
- **Persistence:** `sb/domain/fishing/store.py` `FISHING_ENERGY_STORE` (a `register_store(StoreSpec(...))` with `bears_value=False`, `data_class=MEMBER_ID`, `checkpoint_class=AGGREGATE`, `forward_map_kind=NAME_STABLE`, `sole_writer=EngineRef("fishing.store")`, `erasure_ref=WorkflowRef("fishing.erase_subject_energy")`) + `get_fishing_energy`/`set_fishing_energy`. For mining, energy rides the **existing** `mining_player_state` store (add `get_energy`/`set_energy` to `sb/domain/mining/store.py`), NOT a new store — matching the oracle.
- **Consumer seam (non-money lane):** `sb/domain/fishing/service.py` `cast_open` (lines 60-92) is the exact pattern — `get_*_energy → EnergyState → settle → can_* gate (refuse w/ regen-wait copy) → spend → set_*_energy`, a **plain game-state upsert, no audited-write op, no advisory lock** (store.py comment: "energy is game pacing, never coins — the shipped read carried no lock"). Energy is deliberately NOT routed through the K7 audited money seam.
- **Migration precedent:** `migrations/0035_fishing_energy.sql` (`CREATE TABLE fishing_energy ... energy INTEGER DEFAULT 60, energy_updated_at BIGINT DEFAULT 0`). For mining, an **ALTER** on the existing `mining_player_state` (next migration ≥ 0049; #313 shipped 0048): `ADD COLUMN energy INTEGER NOT NULL DEFAULT 0, ADD COLUMN energy_updated_at BIGINT NOT NULL DEFAULT 0` — DEFAULT 0/0 is the faithful missing-row `(0,0)` posture (existing depth-players settle to full on first read).
- **Erasure:** `sb/domain/fishing/ops.py:148` `fishing.erase_subject_energy` workflow + ref row — mining energy on `mining_player_state` is already erasure-covered by the existing player-state erasure (verify no new erasure ref needed since it's an existing table/store).

### The exclusion note (where the WP lane deferred cook/use)
- Claim: `control/claims/mining-write-parity-lane.md:23-26` (quoted in Step 0).
- Live code: `sb/domain/mining/service.py:894-925` — `cook_route`/`use_route` bare invocations answer the oracle usage copy (pinned green by `sweep_cook.json` / `sweep_use.json`); the **argful** path returns the honest BLOCKED pending copy ("🔥 `!cook` needs the mining campfire/energy system…" / "🎒 `!use` needs the mining consumable/energy system…").
- `PENDING` dict comment `service.py:979-984`: "the argful cook/use energy lanes stay deferred (deep-game-ports pending terminals)."
- Cross-reference: PR #313 body — "PR #306 (deep-mining WRITE-PARITY lane) and its **named-separate cook/use energy lane** are mining-side."

### Migration + gate work a new energy-consuming command requires
- New migration (ALTER `mining_player_state`, ≥0049) + `check_migrations` clean.
- `manifest.snapshot.json` recompile IF the PENDING dict / routes change (cook_route/use_route are already registered handlers — flipping BLOCKED→LIVE is a handler-body change, no new command rows, but the `PENDING` roster comment updates).
- `check_sim_gate` — no new panels/actions for cook/use (existing text commands), should stay green.
- `check_money_race` — energy is a non-money lane (fishing precedent: plain upsert, no `FOR UPDATE`); no new money-race obligation. (NB: a concurrent double-`!use` could double-restore under no lock — the oracle ships it lockless, so faithful = lockless; flag as a known-parity posture, not a fix.)
- New argful goldens via `sb/adapters/parity/runner.capture_case` (RNG-seeded, clock-frozen, TRUNCATE…RESTART IDENTITY, fixtures pre-snapshot). `check_parity_depth` ratchet if new mining stores/events register (energy on existing `mining_player_state` → likely no NEW table row, but the energy-column write becomes a covered face).

---

## STEP 3 — VERDICT

### VERDICT: **HYBRID — a genuine OWNER DECISION on the keystone, plus a zero-blast-radius clean slice that lands regardless.**

**Why not a clean slice-only port:** The oracle energy system exists *to gate digging* — it is "the frequency brake the owner chose instead of a per-dig cooldown." Its keystone consumer is `mining_workflow.mine` (DIG_COST spend + 0-energy refusal), driven by `!fastmine`. But in superbot-next, `!fastmine` is **already ported, LIVE, and golden-pinned WITHOUT energy** (`sweep_fastmine.json` db_delta = `[ai_decision_audit, game_xp, mining_inventory, xp]` — no `mining_player_state`, no energy write, no refusal path). Wiring energy faithfully:
1. **Re-mints a green, already-frozen golden** (`sweep_fastmine`) — adds a `mining_player_state` energy-column write to its db_delta.
2. **Collides on `mining_player_state` with WP-3 (#317, OPEN)**, which is mid-flight re-freezing that exact table's contract + ratchet.
3. **Contradicts the next port's explicit "core loop (mine/chop/explore/sell/buy) is live" framing** — a plausibly-intentional owner choice to keep the core loop ungated.
4. Without dig-spend, **cook/use are degenerate**: energy is always full, so `!use ration` always returns "Your energy is already full — save it for later." and `!cook` mints food that can never be usefully eaten. Cook/use are only *meaningful* once dig spends energy — so the whole system hinges on the dig decision.

The pure-domain core + unit tests, however, mirror `sb/domain/fishing/energy.py` exactly and disturb nothing — they can land regardless of the decision.

### SIX-FIELD OWNER ASK

**(1) Decision needed**
Do we make mining energy a **live resource** in superbot-next — i.e. wire `energy.spend(DIG_COST)` + the 0-energy refusal into the already-ported `!fastmine`/dig leg (oracle-faithful), which re-mints the green `sweep_fastmine` golden and mutates the `mining_player_state` contract WP-3 is mid-flight on — **OR** port energy as a **dormant/consumption-only** system (cook/use terminals + domain + persistence) and leave the core mine loop ungated for now?

**(2) Context**
The oracle (`disbot/utils/mining/energy.py`, migration 086) makes energy the deliberate frequency brake on digging: `!fastmine`/`!mine` → `mining_workflow.mine` spends `DIG_COST=1` and refuses at 0 with "⚡ You're out of energy…". superbot-next ported `!fastmine` earlier WITHOUT energy (`sweep_fastmine.json` is green and carries no energy write) and framed "the core loop is live" as a feature; the deep-mining WRITE-PARITY lane then explicitly carved cook/use into "a **separate lane**" because they "depend on the un-ported mining energy/consumable system." That separate lane is this port. Energy persists on `mining_player_state` — the same table WP-2 (#312) and WP-3 (#317) are currently re-freezing.

**(3) Options**
- **A — Full faithful port (dig gated):** wire energy into `record_mine`/`fastmine` + cook/use. Maximal fidelity; the mine loop gets the oracle's brake. Re-mints `sweep_fastmine`; must sequence AFTER WP-3 (#317) lands to avoid a `mining_player_state` db_delta/ratchet fight.
- **B — Consumption-only port (dig ungated):** port the energy domain + persistence + wire ONLY cook/use; leave `!fastmine` energy-less. No green golden re-minted, no WP-lane contention — but cook/use are degenerate (energy always full) and the system diverges from the oracle's core purpose.
- **C — Domain-core-only now, defer both consumers:** land the pure `sb/domain/mining/energy.py` + unit tests (zero blast radius, mirrors fishing), and hold the wiring decision (A vs B) until WP-3 merges and the owner rules.

**(4) Recommendation**
**C first (immediately, unconditionally), then A — but sequenced strictly AFTER WP-3 (#317) merges.** C is a free, faithful, zero-risk foundation. A is the only reading that honors the faithful-port posture (the oracle's energy IS the dig brake; B ships a system that contradicts its own reason to exist and produces degenerate cook/use). A's blast radius is real but bounded and fully mitigated by waiting for the `mining_player_state` WP work to settle, then re-minting `sweep_fastmine` in the same slice as the dig wiring.

**(5) Blast radius / risk**
- Re-mint of `sweep_fastmine.json` (a currently-green, merged golden) — changes a frozen contract; must be captured via the canonical harness, not hand-edited.
- `mining_player_state` db_delta + `check_parity_depth` ratchet contention with WP-2 (#312) / WP-3 (#317) if not sequenced after them.
- Lockless concurrent `!use` can double-restore (oracle ships it lockless — faithful, but a `check_money_race` reviewer may flag; ledger as accepted parity posture).
- Migration ordering vs #313's 0048 (use ≥0049).
- Option B risk: shipping a divergent, self-contradicting energy system (degenerate cook/use) that a later "make dig spend energy" change would have to re-open anyway.

**(6) What's blocked until answered**
- The `!cook` and `!use` argful terminals (`service.py:894`, `:911`) stay honest deep-game-ports BLOCKED pending terminals.
- The final green report leg for the mining subsystem (energy is the last un-ported mining deep-system; status.md ⚑ needs-owner #1).
- Only the *wiring* is blocked; **slice 0 (domain core + unit tests) is NOT blocked and should proceed now.**

### CONDITIONAL SLICE PLAN (executes on decision; ordered)

**Slice 0 — energy domain core (UNBLOCKED NOW, zero blast radius).**
- Files: `sb/domain/mining/energy.py` (NEW), `tests/unit/band?/test_mining_energy.py` (NEW; mirror oracle `tests/unit/utils/test_mining_energy.py` — cap, partial-regen preservation).
- Carry verbatim: `MAX_ENERGY=60`, `DIG_COST=1`, `REGEN_SECONDS=10`, `RESTORE_VALUES={"ration":25,"energy drink":50,"cooked fish":30}`, all 7 functions, the `⚡ {c}/{max} [▰…▱]` bar.
- Gate: unit only. Headless-first; disturbs no golden.

**Slice 1 — persistence + migration (audited-seam-mirror).**
- Files: `migrations/00XX_mining_energy.sql` (ALTER `mining_player_state` ADD `energy`, `energy_updated_at` DEFAULT 0/0), `sb/domain/mining/store.py` (`get_energy`/`set_energy`, plain upsert — the `mining_player_state` sole-writer, NON-audited/non-money, per the fishing precedent). Verify existing player-state erasure covers the new columns.
- Gate: `check_migrations` clean; unit round-trip test; NO new store row (energy rides the existing `mining_player_state` store).

**Slice 2 — wire `!use` + `!cook` terminals + argful goldens.**
- Files: `sb/domain/mining/service.py` (`use_route`/`cook_route` BLOCKED→LIVE), `sb/domain/mining/ops.py` (cook one-txn fish-debit+cooked-fish-grant; use restore+item-debit), `sb/manifest/mining.py` + `manifest.snapshot.json` (PENDING roster update, no new command rows).
- Carry verbatim: campfire gate copy, cook success line (`🔥 You cook **{qty}× {fish}** into **{qty}× cooked fish** (+30 ⚡ each…)`), use refill line (`You consume **{item}** and recover energy ({bar}).`), full-energy refusal, torch/dynamite/generic flavour.
- Goldens (canonical harness): `!use ration` restore, `!use ration` when-full refusal, `!cook minnow` with campfire, `!use torch` flavour. Bare `sweep_cook`/`sweep_use` STAY green (already oracle usage copy).
- Gate: golden-parity gate, `check_parity_depth`, `check_sim_gate`, `check_money_race` (ledger the lockless posture).

**Slice 3 — wire dig energy-spend into `!fastmine` (ONLY under Option A; sequence AFTER #317).**
- Files: `sb/domain/mining/ops.py` `record_mine` (get_energy→can_dig gate→spend→set_energy), `sb/domain/mining/service.py` `fastmine_route` (out-of-energy refusal path).
- Carry verbatim: out-of-energy hint `"⚡ You're out of energy — rest a moment (~{wait}s until your next dig) or eat a **ration** / **energy drink** (`!use ration`)."`
- Goldens: **re-mint `sweep_fastmine.json`** (now writes `mining_player_state` energy 60→59) + a new out-of-energy-refusal golden.
- Gate: full golden-parity + ratchet reconcile against the post-WP-3 `mining_player_state` contract.

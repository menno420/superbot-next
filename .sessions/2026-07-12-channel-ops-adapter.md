# 2026-07-12 — channel-ops adapter enabler (the D-0030 named successor's port + twin + compensator ruling, D-0077)

> **Status:** `in-progress`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194 / ORDER 012)

## Scope

The setup/quicksetup wall's ENABLER half, deliberately WITHOUT the
flip: parity stays 48/50 and the gate stays 355/355 by construction.
D-0030 (decisions.md:227) names "the channel-ops port + these handlers"
as the successor slice; the quicksetup team-memory wall record names
the two missing enablers verbatim — no create-channel capture twin, no
ruled create-channel compensator class. This slice ships exactly those
enablers plus the port surface they hang off, and rules the compensator
class as D-0077.

## Delivered

- `sb/domain/channel/service.py` — `ChannelStateActions` grows
  `create_text_channel` (overwrites passed AT creation as the new
  `ChannelOverwrite` entries — the oracle's
  guild_resources.ensure_channel create path; returns the created
  channel id) and `delete_channel` (live-adapter contract:
  NotFound-as-success; name/id guards stay in the calling domain).
  Fail-loud `_NoActions` default extended — an unarmed port refuses,
  never silently succeeds. Get-before-create/idempotent reuse is ruled
  DOMAIN logic (the oracle's ensure_setup_channel), never the port's.
- `sb/adapters/parity/transport.py` — `ParityChannelStateActions`
  records the corpus's own verbs: `create_channel` (args
  `{guild_id, type: 0, reason}`, payload
  `{name, parent_id, permission_overwrites}` with INT masks, created id
  minted off the SHARED allocator — the golden's `<msg:1>`) and
  `delete_channel` (bare `{channel_id, reason}`). Byte truth:
  goldens/_unmapped/sweep_setup.json + sweep_del.json +
  fake_http.create_channel/delete_channel. Zero boot change — the twin
  was already armed per-case.
- `sb/domain/setup/ops.py` (new) — `setup.compensate_create_channel`,
  the D-0077-ruled compensator (proof_channel.compensate_unlock shape:
  fork-E conn=None handler + ensure_ops_refs re-arm seam): id-guarded
  (deletes only `ctx.params["_created_channel_id"]`, no-op without the
  stash), best-effort (refused delete → operator finding +
  `deleted: False`, never a raise), NotFound-as-success via the port
  contract. No CompoundOpSpec declared — the setup domain has no ops
  home yet and declaring the op is the flip lane's move.
- `docs/decisions.md` D-0077 — the ruling + the oracle contrast the
  flip lane needs: the oracle's setup lane sequences create BEFORE any
  DB write and never rollback-deletes (deletes are separate deliberate
  cleanup, name-guarded), so a faithful port may run the create inside
  the DB leg (the moderation.timeout D-0065 posture) and need no
  compensator — but a create leg AFTER a DB leg MUST declare this one.
- Tests: `tests/unit/setup_band/test_channel_ops_enabler.py` (fail-loud
  default, install path, compensator ref resolution + all three ruling
  semantics) + `tests/unit/parity_adapter/test_channel_ops_capture.py`
  (both wire shapes verbatim, shared-allocator interleave).

## Evidence

- Baseline BEFORE changes (Postgres re-provisioned per the ops-note
  recovery: cluster restarted, role `parity` + parity/parity_replay/
  superbot recreated): check_parity_depth OK (471 goldens),
  `run_golden_parity --gate` GREEN 355/355 across 48 ported.
- After changes: gate 355/355 unchanged, full unit suite green,
  check_money_race untouched/green (no money-domain files in the diff).

## Depth finding (for the flip lane)

The setup/quicksetup SLASH goldens record ZERO channel calls — the
trap-17 leaked-workspace reuse means the corpus's create_channel
vocabulary lives only in the `_unmapped` sweeps (sweep_setup.json mints
`<msg:1>` and the slash sweeps reuse it with no create of their own).
The twin therefore speaks the `_unmapped` shape; the flip lane still
owns the trap-17 disposition (honest ensure-create records an EXTRA
call the slash goldens lack; capture-faithful reuse needs a ruled
pre-existing-channel seam) plus the pending-terminal retirements and
the D-0019-class corpus ruling if the goldens are re-cut.

## 💡 Session idea

The flip lane's cheapest first move is quicksetup (1 golden) via a
setup compound op that mirrors the ORACLE's sequencing — create inside
the DB leg (D-0065 posture, no compensator needed) with the ephemeral
reply's jump link woven from the twin-minted id — leaving the 8-golden
setup row (and its two walled members) for the owner-shaped trap-17
ruling D-0076-style: build the machinery, park the blocked declaration.

## ⟲ Previous-session review

The wave-7 wrap-up card (#241) closed the parity-flips lane clean and
its status fold named the successor queue precisely ("GuildRoleActions,
ChannelPermActions still unarmed"), which made this slice's port-home
question (extend ChannelStateActions vs invent a parallel protocol) a
lookup instead of a debate. What it under-specified: the walls
themselves — "PARKED trap 17 / BLOCKED D-0030" names the blocker but
not the enabler inventory; this session had to reconstruct the oracle's
setup provisioning from search fragments to learn the compensator
question even had an EFFECT-before-DB answer. Wall records should name
the enabler list, not just the blocking decision id.

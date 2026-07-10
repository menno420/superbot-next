# 2026-07-10 — hermes parity flip (/bugreport + /dispatch unconfigured-bridge reply)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `hermes` parity subsystem pending→ported: make both goldens
(`parity/goldens/hermes/sweep_slash_bugreport.json`,
`sweep_slash_dispatch.json`) replay byte-green against the new bot.
Oracle: menno420/superbot `disbot/cogs/hermes_cog.py` (HermesCog — the
Discord→Claude-Code dispatch bridge; owner-ruled `drop` from the new
bot's product surface 2026-07-05, carried here at parity fidelity only).

## What shipped

1. **`sb/domain/hermes/`** — bridge-config presence seam
   (`install_hermes_bridge_config(cfg)` at K0, fails closed uninstalled —
   the parity harness's natural posture), the static
   `hermes.bridge_unconfigured` panel (the shipped red missing-config
   embed: `discord.Color.red()`, no footer, no components), and thin
   handlers: unconfigured → panel on the deferred followup; a keyed
   bridge hits an honest pending terminal (the outbound Routine-`/fire`
   POST is un-ported egress — deliberate, given the owner's drop ruling).
2. **`sb/manifest/hermes.py`** — both commands slash-only, ADMIN-floor
   authority (shipped `default_permissions(administrator=True)`),
   `reply_visibility=EPHEMERAL` (shipped `safe_defer(ephemeral=True)`);
   surface-default `DeferMode.AUTO` gives the goldens' type-5 ack.
3. **Transport twin followup shape** (`sb/adapters/parity/transport.py`)
   — `followup_send` now records discord.py's `Webhook.send` wire shape:
   `webhook_id` is the BOT user (all 6 corpus followups pin `<@bot>`) and
   `content`/`components` are omitted when absent; the type-4
   interaction-response shape is untouched (goldens/help pin it).
4. **`red` style token** (15158332) in `STYLE_TOKEN_COLORS`.
5. **Compat pin amended** (`--write`, same-PR rule): `hermes` subsystem
   key + 2 commands; snapshot recompiled (42 manifests); sim-gate
   baseline carries the two `help_section_order` legacy-seed rows (the
   same exempt provenance as every other shipped command's ordering).
6. **Tests** — `tests/unit/parity_adapter/test_hermes_followup.py`:
   followup wire shape, fail-closed config seam, a db-free end-to-end
   slash drive asserting the goldens' exact call pair, and a
   golden-bytes ↔ `MISSING_CONFIG_HELP` pin.

## Verification

- `run_golden_parity --gate`: GREEN — hermes 2/2 on top of help 3/3,
  rps_tournament 1/1, leaderboard 1/1 (real Postgres).
- `check_parity_depth`: R2 100% trivially (hermes declares no events/
  tables/settings), R3 ratchet row `hermes: {events: 0, tables: 0,
  settings: 0}` minted at the flip.
- Full checker fleet + pytest green.

## Parked / follow-ups

- The configured-bridge transmit lane (Routine `/fire` POST) is an
  honest pending terminal — if the owner ever revisits the drop ruling,
  it needs an egress-declared adapter + compensator review.
- Mid-slice hazard: this session shared its checkout with the
  leaderboard lane (#118/#119) and briefly committed onto
  `parity/leaderboard-flip` (local only); recovered by cherry-pick onto
  this branch after the lane merged.

## 💡 Session idea

The corpus's four *other* `followup_send` consumers (karma ×2, economy,
setup) now have their wire shape pre-cleared by this slice's transport
fix — a cheap sweep: replay those pending subsystems' followup cases and
record which are green-but-unflipped, so their port slices start from an
honest residual-diff list instead of rediscovering the webhook-shape
class this slice already killed.

## ⟲ Previous-session review

The leaderboard flip card's `--write-ratchet`-is-destructive warning was
load-bearing here: this slice hit exactly that (trial-ran the tool, saw
the comment wipe, restored and hand-edited the two-line diff instead).
Its "one specific review question to @codex" pattern also carried over.
What it could not warn about: two lanes sharing one working checkout —
this slice's runtime commit briefly landed on the leaderboard branch
(reflog-recovered; see Parked). Worth a standing note in the worker
protocol rather than per-card folklore.

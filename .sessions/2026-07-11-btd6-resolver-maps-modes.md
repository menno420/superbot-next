# 2026-07-11 — btd6 resolver maps/modes matching (band 7, the #144 parked domain item)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194 / ORDER 012)

## Scope

The smallest-risk item on the #144 parked DOMAIN list (freeplay MOAB
scaling · **resolver maps/modes** · boss estimator · CT-team flow ·
seed-data terminals): the shipped resolver's maps/modes entity matching,
which #144 ledgered as "the resolver does not match maps/modes yet —
test-intent renders their rows honestly as `—`". Chosen over freeplay
MOAB scaling because it is fully self-contained on the committed dataset
(maps.json / modes.json already in `sb/domain/btd6/data/`), needs zero
manifest/schema/golden movement, and its oracle surface reconstructed
cleanly fragment-by-fragment.

## Oracle reconstruction (trap 24 ledger)

search_code fragments returned refs **d647b2e9** and then **7349c8a7**
mid-session (the oracle default branch churned again, past the 2c7d2de7
head the previous slice ledgered; corpus pin stays `7f7628e1`). Sources
reconstructed: `disbot/services/btd6_resolver_service.py` (the
maps/modes alias-map loops + matched_count), `disbot/services/
btd6_response_builder.py` (`for_map` / `for_mode`, complete bodies),
`disbot/services/btd6_knowledge_service.py` (`map_fact`/`mode_fact` =
bare `get_map`/`get_mode`), `disbot/services/btd6_ai_service.py` (the
deterministic_answer precedence order "towers → heroes → maps → modes →
rounds → bloons"), `disbot/cogs/btd6/_embeds.py` (the test-intent
Maps/Modes rows: `", ".join(m.canonical …) or "—"`), and the oracle's
own `tests/unit/services/test_btd6_resolver_service.py` CHIMPS pin.
Fragments were diffed against the goldens FIRST (trap 24 discipline):
the only golden touching this surface pins the EMPTY state ("test" →
all `—`, confidence 0.00) — no capture-sha drift risk on pinned bytes.

## What shipped

1. **sb/domain/btd6/dataset.py** — typed `MapEntry` / `ModeEntry` +
   `maps()` / `modes()` / `get_map()` / `get_mode()` accessors (the
   shipped parse posture: blank `removables` = "no data", modifiers
   carry None cash/lives; `wiki_url` attribution-only, not carried).
2. **sb/domain/btd6/resolver.py** — `ResolvedIntent` grows `maps` /
   `modes`; matching rides the SAME shipped `_match_terms` discipline
   (multi-word substring, single-word whole-token + plural fold),
   including the shipped common-word quirk ("hard"/"reverse"/"standard"
   token-match inside ordinary sentences — carried, never "improved");
   matched_count includes both families (oracle fragment verbatim).
3. **sb/domain/btd6/oracle_cards.py** — `for_map` / `for_mode` at the
   oracle's reconstructed bytes (title `"{canonical} ({difficulty})"` /
   `"{canonical} mode"`, the removables append, the cash/lives bits
   guards, `recommended_options=mode.restrictions`, for_map's
   follow_up literal); `deterministic_answer` gains the maps → modes
   branches in the shipped order; `test_intent_card` Maps/Modes rows now
   render matched canonicals (empty state byte-identical to the golden);
   the module-docstring deviation ledger updated (maps/modes bullet
   retired; MOAB scaling + estimator bullets stand).
4. **sb/domain/btd6/context.py** — docstring-only honesty note: in the
   oracle, matched maps/modes feed ONLY the `btd6_facts` DB grounding
   pass (D-0046 successor, unported) — no fixture facts render for
   them, matching shipped; `build()` behavior untouched.
5. **tests/unit/band7/test_band7_btd6_maps_modes.py** — 17 tests: the
   oracle's CHIMPS scenario, substring/token/alias matching, the
   common-word quirk pin, confidence growth, both card byte pins
   (incl. modifier None-handling + curated removables), the shipped
   precedence order (tower beats map, map beats round), and the
   golden's empty-state bytes pinned exactly.

Zero new commands/panels/modals/events/tables/settings; no parity.yml,
ratchet, compat, sim-gate, or lock-file movement; no exemptions, no new
reason classes, compensator allowlist EMPTY (read-only slice, no ops).

## Ladder (serial, real Postgres — trap 25)

units **1452 passed / 2 skipped** (canonical order; +17 = this file);
gate **GREEN 253/253** across 37 ported; report **291/467 green,
467/467 replayable** (btd6 41/41 — all counts unchanged from the #204
head: the slice mints zero goldens); check_parity_depth OK (49
subsystems, 467 goldens); manifest_compile / namespace / sim-gate /
compat / intent-survival / slash-cap / escape-hatches / schema-growth /
amendments / symbol-shadowing / no-skip / config-usage /
metric-cardinality / egress all clean.

## Parked (unchanged, honest)

Freeplay MOAB scaling (the `bloon_rbe_at_round` spawn-tree walk), the
boss estimator arm, the CT-team guided-set flow (live NK bracket), the
`!btd6 ops seed-data` terminal — still on the #144 parked list. The
oracle's maps/modes `btd6_facts` grounding pass and the `!btd6 map` /
`!btd6 mode` command surfaces (if any capture exists — none in the
corpus; trap 28 check found no sweep skip rows for them) ride D-0046.

## 💡 Session idea

The parked-item ledger in oracle_cards.py's docstring proved to be the
exact scope contract for this slice — porting future parked items
should start by grepping for their own ledger sentence and end by
retiring it in the same diff, so the deviation ledger can never drift
stale-positive.

## ⟲ Previous-session review

D-0074's card named trap 24's churn with exact refs, which made the
"diff fragments against goldens FIRST" step reflexive here — the
empty-state golden check happened before any code was written. The
three-slice parked-term → port → retire-the-ledger loop from
D-0071/72/74 transferred to a pure-domain (no-panel) slice unchanged.

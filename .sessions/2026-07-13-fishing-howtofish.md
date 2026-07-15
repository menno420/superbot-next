# 2026-07-13 — fishing: the 🎣 how-to-fish hub guide port

> **Status:** `complete`

- **📊 Model:** Claude (Fable family) · high · feature build
  (branch `claude/fishing-howtofish` — the #405 completeness-remainders
  claim, fishing row)

## Scope

Port the fishing hub's LAST pending affordance — the 📖 **How to fish**
button (`fishing_rules`, `sb/domain/fishing/panels.py` hub spec), which
routes to the `fishing.howtofish_pending` terminal today — onto the
declared panel grammar, oracle-verbatim (the
`docs/status/completeness-table-2026-07-13.md` fishing-row residue named
by the #405 claim).

Oracle source (LOCAL clone /home/user/superbot @ `9776401`):
`disbot/views/fishing/menu.py::_rules_embed` — the "how to fish"
quick-reference the menu's 📖 rules affordance sends as an EPHEMERAL
component reply (`rules_btn`, mirroring the blackjack panel's rules
affordance): title `📖 How to fish`, the loop/get-better-catches
description, `GAME_COLOR` purple, no fields, no footer, no components.

Planned shape (the creature `rules_card` precedent, mirrored exactly —
`sb/domain/creature/panels.py::rules_card_spec` +
`service.py::rules_view`):

- `fishing.rules_card` (NEW PanelSpec, `sb/domain/fishing/panels.py`):
  fully STATIC card, grammar-rendered, no override — purple frame,
  `FooterMode.NONE`, the oracle description verbatim as one `TextBlock`,
  zero actions, no nav (an ephemeral quick-reference, the creature
  rules-card posture).
- `fishing.rules_view` (NEW handler, `sb/domain/fishing/service.py`):
  the hub button's route — opens the card.
- Hub `fishing_rules` button repoints
  `fishing.howtofish_pending` → `fishing.rules_view` +
  `reply_visibility=EPHEMERAL` (the shipped `ephemeral=True` send);
  label/emoji/style untouched — byte-neutral vs
  `goldens/fishing/sweep_fishing` (the Dex-button repoint precedent).
- `fishing.howtofish_pending` RETIRED (`_register_hub_pending` removed —
  trap 12a: a retired pending ref must no longer register).
- Manifest: `rules_card_spec()` joins `sb/manifest/fishing.py` panels;
  `manifest.snapshot.json` recompiled.
- Golden per D-0073: a curated GoldenCase (`!fishing` → click the 📖
  How-to-fish button by component_index) minted via the canonical
  capture path, double-captured for determinism; corpus count pins +
  `parity.yml` `minted_goldens` bumped.
- Unit tests: the venue/rod/bait/structures slice-test pattern — hub
  repoint + retirement + card bytes + compile fences.

## Verification

Shipped as PR #410 (`claude/fishing-howtofish`), post-merge of
origin/main @ `347dfba` (#408 — the sibling completeness-remainders
cleanup slice; its concurrent golden mint moved the same corpus pins,
reconciled at merge: on-disk 493 = 465 + 31 − 3, `minted_goldens`
30→31, the three count-pin call sites re-summed by hand):

- `python3 -m pytest tests/ -q` (local Postgres DOWN — the banner-test
  posture): **2779 passed, 15 skipped**.
- `python3 tools/run_golden_parity.py --gate` (local Postgres up):
  **GREEN — all 493 golden(s) across 50 ported subsystem(s) replay
  clean**, including the new `fishing_howtofish_rules_card` (minted via
  the canonical capture path only, double-captured across fresh harness
  boots — byte-identical ×2; pins the ephemeral defer flags-64 + the
  verbatim rules embed, NO components, no fishing db_delta — a pure
  read, only the message-driven xp.award pair).
- `tools/check_parity_depth.py` OK (493 goldens; fishing ratchet
  untouched — a pure read moves no covered floor);
  `manifest_compile` green; `check_compat_frozen` OK against the
  EXISTING pin (no custom_id_override, no modal — no regen needed);
  namespace / shadowing / no-skip / config-usage clean.
- `bootstrap.py check --strict`: exit 0 (the born-red hold flips with
  this landing commit; one pre-existing claims-format advisory on
  another lane's claim file).
- `sweep_fishing` byte-neutral (label/emoji/style untouched — the
  repoint rides the Dex-button precedent); the retired
  `fishing.howtofish_pending` no longer registers (trap 12a, pinned by
  tests/unit/band6/test_band6_fishing_howtofish.py).

## 💡 Session idea

The corpus count pins are a concurrent-mint collision magnet: this
slice and #408 each minted ONE golden and each bumped the SAME four
call sites (491→492 / 29→30 in parity.yml,
test_replay_adapter.py, test_check_parity_depth.py ×2), so the merge
had to re-sum every site by hand to 493/31 — and nothing but reviewer
arithmetic catches a miss. Derive, don't pin: keep the single
authoritative triple (imported/minted/retired) in parity.yml and have
the tests assert `on-disk == imported + minted − retired` against IT,
plus one test asserting the parity.yml enumeration paragraph count
matches `minted_goldens`. Concurrent mints then conflict on exactly
one integer in one file, and the prose ledgers stop being load-bearing
arithmetic.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-cleanup-pending-actions.md` @ `347dfba` —
the lane's item-2 slice, PR #408.) Load-bearing and accurate: its
re-derive-at-HEAD posture ("the completeness table has been stale in
both directions") is why this slice re-traced
`fishing.howtofish_pending` to the live hub button before building —
the row proved REAL, unlike the role trio false positives it flagged.
Its parity.yml mint-ledger paragraph was the direct template for this
card's golden entry, and its 💡 (`tools/mint_golden.py --case <id>`)
was proven right within hours: this session re-invented exactly that
scratch script (boot Harness → capture ×2 → compare → write
golden_path) — third re-invention on this corpus; build the tool. One
gap: its card didn't flag that a concurrent sibling mint would collide
on the shared count pins — this slice's merge hit exactly that, and
the 💡 above is the structural fix.

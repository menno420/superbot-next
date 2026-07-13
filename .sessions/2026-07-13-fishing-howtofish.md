# 2026-07-13 — fishing: the 🎣 how-to-fish hub guide port

> **Status:** `in-progress`

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

(filled at completion — the strict gate holds this card red until the
branch lands green)

## 💡 Session idea

(filled at completion)

## ⟲ Previous-session review

(filled at completion)

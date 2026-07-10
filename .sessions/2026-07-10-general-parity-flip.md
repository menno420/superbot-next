# 2026-07-10 — general parity flip (pending→ported, the fourth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Port the `general` subsystem's golden-pinned surface and flip its
`parity.yml` row pending→ported through the A-16 door — the help-flip
playbook applied to the shipped General menu panel. Oracle:
menno420/superbot `disbot/cogs/general_cog.py` (`GeneralMenuView` +
`_overview_embed`); golden:
`parity/goldens/general/sweep_generalmenu.json` (case
`sweep.generalmenu`, the subsystem's only golden).

## What shipped

1. **`!generalmenu` opens the shipped General menu** —
   `sb/domain/general/` + `sb/manifest/general.py`: a session-lifecycle
   PanelSpec (`general.menu`) with the shipped bytes — title
   `💬 General`, discord.Color.green() (new `green` style token,
   3066993), the 7-line command legend, three button rows
   (Fact/Joke/Quote blurple · Trivia/Motivate/8-Ball grey ·
   Greet green + ↩ Overview), emoji INSIDE the labels (the shipped wire
   shape). Run-minted custom_ids (#117) symbolize to `<cid:N>`; no
   `panel_anchors` row (#118). Replayed byte-green on first try — the
   two enablers cleared every residual class in advance.
2. **Thin content handlers** — `general.fact_view`/…/`greet_view` +
   the G-10 8-Ball question modal (`general.eightball_answer`), all
   read-only over `sb/domain/general/content.py`.
3. **Sim-gate seed arrangement** — `manifest/layout/general.lock.json`
   legacy-seed Exempt rows (8 actions > the panel floor of 4) +
   baseline regen, the band-3/4 precedent.
4. **The flip**: `parity.yml` `general: ported` + the A-16 ratchet row
   `general: {events: 1, tables: 2, settings: 0}` (minted via
   `--write-ratchet`, re-applied by hand to keep the file's comment
   header — same counts). R2 is vacuous (no declared surfaces); zero
   exemptions.

Gate leg: 6/6 goldens across 4 ported subsystems GREEN against real
Postgres. Dashboard moves 3 → 4 ported (of 49); report leg 17 → 18
green (of 465). Full suite 1169 passed.

## Content-pool provenance (deliberate under-port)

`sb/domain/general/content.py` carries ONLY entries verified verbatim
against the oracle's `data/json/general_content.json` (code-search
fragments; direct oracle file reads are denied in this session). Pools
with no verified entries (motivations, greetings, 8-ball answers) ship
EMPTY behind the shipped fallback string (`No {label} available.`,
general_cog.py verbatim) — honest waiting surface, never invented
content. No golden pins any pool entry. **Parked follow-up:** import
the shipped JSON byte-verbatim; also parked: the 7 sibling prefix
entry points (!fact, !joke, !quote, !trivia, !motivate, !eightball,
!greet — same handlers, entry-point declarations only).

## 💡 Session idea

The flip needed FOUR sim-gate Exempt rows + a baseline regen for what
is semantically ONE decision ("carry the shipped arrangement"):
`PanelSpec.layout`, `LayoutSpec.pages`, `PageSpec.rows` triple-pin the
same rows tuple. A single layout-level assignment key (or the checker
collapsing the three into one) would make a port's overlay diff match
its decision count.

## ⟲ Previous-session review

The leaderboard-flip card's warning that `--write-ratchet` destroys the
parity.yml comment header was exactly the trap this session avoided on
the first pass — the restore-and-hand-apply dance worked as documented.
What it under-delivered: it did not mention the SIM gate as a flip-time
cost (leaderboard's board panel sat below the 4-component floor, so its
flip never saw the gate) — an 8-button panel port trips 4 unpinned [A]
assignments, and the legacy-seed Exempt precedent had to be
re-excavated from the band-3 economy lock file.

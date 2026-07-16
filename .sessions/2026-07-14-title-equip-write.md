# 2026-07-14 — mining title-equip write slice (ORDER 022 (a)3)

> **Status:** `complete`

- **📊 Model:** fable-5

## Scope

Port the mining title-equip surface: a state-derived earned-title Select
on `sb/domain/mining/panels.py::mining_titles_spec` (absent when the
player has no earned titles; oracle caps at 10 options so no windowing),
plus an audited equip WRITE handler through the proper seam with
oracle-verbatim validation and response strings. Oracle read pinned at
`menno420/superbot@bbc524e`: `disbot/views/mining/titles_panel.py`,
`disbot/services/title_service.py::equip`,
`disbot/cogs/mining_cog.py::titles_cmd` (panel open only — no command
form). D-0073 goldens for the new surface, canonical stripped flavor;
CAPTURE_WORLD_WEATHER registered first before any capture.

Definition of done: implemented + tested + goldens minted + PR READY
(parked green under coordinator WP-stack freeze; flips after the owner's
WP sweep).

Build landed: PR #473 (commits 20bcdaf build + 94925d2 goldens/tests),
all 14 CI checks green at 94925d2 (golden-parity + gate included).
Corpus 500 = 465 + 38 − 3; no exemption/ratchet movement
(mining_player_state already covered). Freeze enforcement: the repo's
auto-merge-enabler armed squash automerge at open — disarmed via the
API + `do-not-automerge` label applied (the workflow re-arms on every
synchronize; the label is its carve-out — the #344 precedent).

## 💡 Session idea

The sibling mining legs raise SINGLE-arg `ValidatorError("<sentence>")`
(e.g. `_record_equip`'s "You don't own a **X** to equip." —
sb/domain/mining/ops.py), which renders wrapped in the
"Missing/invalid argument: …" boilerplate, NOT the shipped copy — this
slice hit that exact trap on its first refusal mint and fixed it with
the D-0060 two-arg form. Guard recipe: audit `rg -n 'ValidatorError\('
sb/domain/mining/ops.py` for one-arg calls whose arg is a sentence, flip
them to `ValidatorError("<param>", "<copy>")`, and pin each with a leg
test asserting `err.value.user_copy` (the
tests/unit/mining/test_title_equip.py refusal-face pattern). Their
refusal faces are un-golden-driven today, so the divergence is latent —
cheap to fix before a golden freezes the wrong byte.

## ⟲ Previous-session review

The night windowed-select session (#435) corrected this lane's premise
in its close-out ("title-equip needs an equip-write slice, not
windowing") — that one sentence saved this session from building
windowed-select plumbing for a 10-option surface; premise-correcting
close-out lines earn their keep. The CAPABILITIES ledger also paid off
twice verbatim: the "local oracle clone is classifier-walled → GitHub
MCP pinned reads" entry routed the oracle reads with zero probing, and
the local-Postgres recipe made both mints + the depth checker runnable
in-seat. Friction worth carrying forward: the local full-pytest run
fails 11 integration race tests against the shared Postgres (same
signatures at origin/main e24503f; CI tests job green on the same
head) — a worker verifying locally should treat that class as
environmental and cite the CI run instead.

# 2026-07-18 — D5 e2e-test-harness: sharpen into a decision-ready package

> **Status:** `complete`

- **📊 Model:** opus-4.8 · medium · docs-only

## Scope

Take `docs/design/D5-e2e-test-harness.md` (the tiered e2e proposal — an
in-process adapter tier D5.1 + an optional LIVE guild sweep D5.2, 7 open
questions) from a raw plan to a **decision-ready package**. Ground the
in-process-tier proposal in the actual test surfaces and the discord adapter
seam (verify, don't invent), then:

- Resolve the **agent-decidable** design picks — above all D5.1's central
  fake-`discord`-shim vs installed-library call — as flagged decide-and-flag
  defaults with an honest, seam-grounded recommendation.
- Route ONLY the genuinely **owner-gated** bits (the LIVE-tier token / cadence /
  cost / signer-identity) as one crisp OPEN router entry.
- If the in-process tier is buildable-now with no owner input, FLAG it as a
  recommended executable follow-up (do NOT build the harness here).

Docs-only slice. No `sb/` source edit. Contained + reversible.

## What landed

A `## Decision-ready refinement (2026-07-18)` section in
`docs/design/D5-e2e-test-harness.md` plus one routed OPEN block in
`docs/question-router.md`. No `sb/` source edit; no `D-00NN` token minted (plan,
not landed code).

- **Grounding (verify, don't invent).** The in-process-tier proposal checks out
  against the real seam: `sb/adapters/parity/boot.py`'s `Harness` contract
  (`start` → `send_command`/`invoke_slash`/`click` → `take_calls`/`take_events`
  → `close`) is already the reusable boot the tier clones, and
  `tests/integration/conftest.py` already boots that same `Harness.start()`
  against real Postgres inside the `golden-parity` gate. The adapter band splits
  in a way the doc's original framing conflated: `message_feed.py` /
  `component_feed.py` are duck-typed (**no** module-scope `import discord`),
  while `egress.py` (`discord.AllowedMentions`/`Object`), `command_tree.py`,
  `panel_view.py`, `modal_view.py`, `confirm_view.py`, `responders.py` all
  construct real `discord`/`app_commands`/`ui` types under the CI-absent guard.

- **Tier-A pick resolved (honest flip).** Recommended **discord-installed
  in-process tier first**, not the doc's original "hermetic-fake-first." A fake
  `discord` faithful enough to exercise egress/panel/modal render is functionally
  a second `ParityPresenter` — circular (proves our code against our fake,
  re-creating P1's blind spot). The discord-installed variant rides an
  environment that *already exists and is proven*: the `golden-parity` gate
  installs the lock (`.github/workflows/named-gates.yml:134`) that ships
  `discord-py==2.7.1` (`requirements.lock:218`) and already boots the same
  harness. A hermetic feed-ingress smoke survives as a cheap add-on, not the
  headline.

- **Other agent-decidable Qs resolved as decide-and-flag defaults:** Q3 (minimal
  CUT-1 sweep shape), Q4 (non-blocking degraded-health; response bound < the 75s
  READY bound), Q5 (structural assertions), Q7 (fixed tolerated channel).

- **Owner-gated bits routed:** one crisp OPEN block in `docs/question-router.md`
  for the LIVE-tier go/no-go — token provisioning (Q2), cadence/cost (Q2), signer
  identity (Q6) — with the safe default *"in-process tier now; LIVE tier deferred
  until there's a token + a reason."*

- **Executable-follow-up flag (NOT built here):** the discord-installed
  in-process adapter tier (D5.1) is buildable now with zero owner input — CI env,
  boot harness, placeholder token, and tier-A pick are all already in place. The
  doc carries a highlighted greenlight-ready call so the owner/next agent can
  approve the D5.1 build directly.

## Verification

- `python3 -m pytest -q --ignore=examples` → **3496 passed, 29 skipped** (docs
  slice — no test delta; parity with baseline).
- `python3 bootstrap.py check` → docs-gate **EXIT=0**. Advisory warnings are
  pre-existing (other cards' model lines, `control/status.md`, seat-digest) — none
  from this slice; my `📊 Model` task-class `docs-only` is a valid PL-004 class.
- **Stamp-gate clean:** `grep -rnE 'D-00[0-9][0-9]' docs/ --include='*.md' | grep
  -v docs/decisions.md` shows no single token in 2+ non-ledger docs; both edited
  docs carry **zero** `D-00NN` tokens.
- Guard-fire telemetry delta (`.substrate/guard-fires.jsonl`) committed with the
  flip, not reverted.

## 💡 Session idea

Because the `golden-parity` job **already** imports `discord` and boots
`Harness.start()`, the D5.1 "hermetic vs installed" split is largely a false
economy — but there is a genuinely cheap FIRST slice hiding in it: the duck-typed
`message_feed`/`component_feed` seams (no `discord` import; ingress token-match
mirrors the harness's `send_command`) can be driven by a synthetic-event double in
the pyyaml-only `checkers` env with no fake `discord` module at all. So the very
first landable e2e slice could be a **hermetic feed-ingress smoke** (synthetic
`on_message`/component-click → dispatch fired) shipped even before the
discord-installed tier — a few-hours gate that starts eroding P1's blind spot at
the two modules that need no library. Worth pinning as the ordering hint when D5.1
is greenlit.

## ⟲ Previous-session review

The prior card (`2026-07-18-invariant-verify-import-scope`) closed #568's flagged
sweep/verify-import divergence by *auditing then pinning* — it proved the
divergence inert today (all invariants `scope=GUILD`) and chose a clarifying
comment + a characterization test over a cargo-culted "fix," honoring #568's
pin-real-behavior posture. Good restraint. The relevant contrast for this session:
sibling design refinements (D1/D3) homed `D-00NN` tokens in `docs/decisions.md`
under decide-and-flag because a *slice landed*; this D5 pass deliberately mints no
token because nothing built — the design picks are recommended defaults a future
slice will home when it lands. Keeping the token out of a plan-only doc is the
same discipline the prior card showed: don't stamp permanence onto something still
provisional.

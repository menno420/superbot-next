# 2026-07-13 — night: host-side idle plugin pin (ORDER 019 item 6)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · NIGHT-RUN cross-repo slice · mandate:
  ORDER 019 item 6 — host-side `plugins.lock.json` pin for the REAL
  out-of-tree superbot-idle plugin adapter, closing superbot-idle's
  live wiring gap per its `control/status.md` Next-3 item 1 @ `1f4d774` ·
  claim: `control/claims/night-fishing-verify-idle-pin.md` (#430).

## Scope

Pin the real superbot-idle repo's `plugin/` adapter (dist
`superbot-idle-plugin`, entry point `idle = superbot_idle_plugin.manifest`)
in the committed pin registry `plugins.lock.json`, the way
`tools/plugin_pin.py --write` would write it — installed-but-unpinned is
the plugin twin of leg-A DRIFT (`sb/app/plugin_host.py:241-251`), so
without a host-side pin the real adapter boot-fails at step 9b.

Cross-repo read-only evidence source: menno420/superbot-idle (public),
shallow-cloned to the scratchpad; all writes land in this repo only.

## Verification (citation bundle)

- **The ask, verbatim** — superbot-idle `control/status.md` Next-3 item 1,
  read at idle HEAD `a6906b9` with `1f4d774` confirmed in history: "Host-side
  `plugins.lock.json` pin for the idle adapter (a superbot-next PR, via that
  lane)."
- **Finding: DONE-ALREADY at HEAD, verified for the first time.** The
  committed pin row (`superbot-idle-plugin`, `0.1.0`,
  `sha256:48bf953dc6a91962e4d5841f85435b20eafa7f614f6916be2320be2c8646fe1c`,
  written for the vendored exemplar in #377) also covers the REAL
  out-of-tree adapter:
  - `plugin/superbot_idle_plugin/` at idle HEAD is byte-identical to the
    vendored `examples/superbot-idle-plugin/superbot_idle_plugin/`
    (`diff -r`, only `__pycache__` differs); dist name / version / entry
    point in the real `plugin/pyproject.toml` match the pinned row.
  - `manifest_stable_hash((MANIFEST,))` computed over the REAL repo's
    manifest module (host code path, `sb/app/plugin_host.py:114-130` — never
    hand-computed) equals the committed pin exactly.
  - End-to-end with the REAL dist pip-installed (venv, genuine
    `importlib.metadata` discovery): `python3 tools/plugin_pin.py` verify
    green, exit 0 — `2 plugin(s) admitted: superbot-idle-plugin==0.1.0
    [idle]; superbot-plugin-hello==0.1.0 [hello]`; `--write` reproduces the
    committed `plugins.lock.json` BYTE-FOR-BYTE (`diff` clean).
- **Tests** — `python3 -m pytest tests/ -q`: **2911 passed, 15 skipped**
  (includes `test_plugin_boot_real_exemplar.py`'s pin-match + coexistence
  proofs). `bootstrap.py check --strict`: red at origin/main itself with two
  pre-existing `[stamp]` findings (D-0043/D-0046 double-citation) that the
  sibling `claude/night-stamp-dedupe` lane is fixing — unrelated to this
  card-only diff; no finding names this slice's files.

## What shipped

ZERO byte changes to `plugins.lock.json` (decide-and-flag: regenerating an
identical file is a no-op diff; the minimal reversible landing is this
verification record). PR: **#441**. Follow-up flagged, not taken:
`examples/superbot-idle-plugin/README.md` still says the vendored copy
tracks idle @ `7814045` (PR #85) while it is byte-identical to idle HEAD
`a6906b9` (includes the #86 live-boot fixes) — true up when the exemplar is
next touched.

## 💡 Session idea

The vendored-exemplar ↔ real-repo equivalence this slice proved by hand is
exactly the invariant nothing guards: the in-tree pin tests red only if the
VENDORED copy drifts from the lock, never if the REAL superbot-idle
`plugin/` drifts from the vendored copy. A tiny non-hermetic (cron/night)
check — shallow-clone superbot-idle, `manifest_stable_hash` its manifest,
compare against the committed pin row — would catch upstream adapter changes
the same night they land instead of at the next live boot. Belongs in the
night-verify rotation, not CI (CI stays hermetic by design).

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-curation-night-2.md`.) A strong port card: the
oracle-verbatim citation (`handle_ctteam` @9c16365), the ledgered deviations
(page-swap vs edit-in-place, D-0046 no-active-event byte), and the
golden-safety note (label/emoji/row bytes unchanged) make the review
re-runnable without the chat. Its boot-recon finding — 21 of 27 backlog rows
already shipped — is the same DONE-ALREADY class this slice and the fishing
verify hit; three in one day says night orders should default verify-first.
One ding: the Model line writes `fable-5` where the cards standardized on
family-level `Claude Fable` (the fishing card flagged the same miss a
session earlier).

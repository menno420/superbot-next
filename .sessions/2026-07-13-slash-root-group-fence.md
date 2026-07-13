# 2026-07-13 — slash-root vs subcommand-group compile fence (Finding #3, PR #370)

> **Status:** `in-progress`

- **📊 Model:** `builder-agent` · coordinator-approved slice · mandate: make
  the discord.py `CommandAlreadyRegistered` bug class red the REQUIRED
  headless gate family (the plugin-boot proof's gate) so the next such
  collision is caught statically, not at live boot.

## Scope

Finding #3 on PR #370 was a live-boot-only crash: a manifest declaring a
slash-capable ROOT command named X AND a subcommand GROUP named X compiles
green in CI, then discord.py's `tree.add_command` raises
`CommandAlreadyRegistered` the moment `register_app_commands`
(`sb/adapters/discord/command_tree.py:107-120`) adds the second claimant of
that one top-level tree name — a root `app_commands.Command(X)` (`:120`,
`group==""`) and a top-level `app_commands.Group(name=X)` minted by
`_group_for` (`:89-102`, `:101`).

Add a discord-free compile pass `_p3b_app_tree` in `tools/manifest_compile.py`
that models `register_app_commands` PRECISELY off the joint projected command
set:

- a leaf registers ONLY when slash-capable — projected `surface == "slash"`
  (`kind` "slash", or the slash half of "both"); a PREFIX-only node is filtered
  out;
- a ROOT is `parent_group` None/`""` (`group==""`);
- a top-level GROUP is `parent_group.split(".")[0]` of a **slash** leaf (groups
  are born only from slash-capable commands, mirroring `_group_for`).

Collision = (slash roots) ∩ (slash top-level groups) → a `COLLISION` violation
naming the offending name and the remedy (make the root `kind=prefix`, or
rename). Wired at the P3 boundary so it collects alongside namespace
collisions and rides the SAME `compile_manifests` the corpus gate, the
plugin-boot proof, and `load_plugins` (joint host+plugin compile) run under.

Definition of done: the whole in-tree corpus + the hello exemplar STILL
compile green (zero false positives); a positive test rejects a slash-root +
same-named-group manifest headlessly; a negative test proves the PREFIX-only
root shape compiles clean; a cross-manifest test proves the joint-set catch;
`python3 bootstrap.py check --strict` + `pytest tests/ -q` both green.

## Corpus false-positive result

Zero. The in-tree corpus has 27 slash roots and — critically — ZERO
slash-surface subcommand groups (all 158 grouped command nodes are
`surface=="prefix"`, e.g. `!ai status`, `!aireview preset add`). Four slash
roots (`karma`, `platform`, `pm`, `settings`) share a name with a PREFIX-only
group — the shipped G-6 `!karma`/`/karma` coexistence — and MUST stay green;
the slash-only group filter leaves all four untouched (slash top-groups is the
empty set). A naive "any command with group==X" check would have red-flagged
all four; the precise modeling is load-bearing.

## 💡 Session idea

The check reconstructs the tree-collision condition from the flat namespace
projection (`surface` + `parent_group`) rather than from an actual
`app_commands.Group` tree — a faithful shadow of `register_app_commands`, but a
shadow. A stronger future guard would compile the LIVE manifests into a real
`discord.app_commands.CommandTree` inside the (import-guarded) discord adapter
test lane and assert `add_command` never raises — turning the modeled
invariant into the real object's own verdict. Until discord is present in a CI
lane, the projection shadow is the honest headless proxy.

## ⟲ Previous-session review

The plugin-boot proof (`test_plugin_boot_real_exemplar.py`) established the
pattern this slice rides: a real headless boot path (`load_plugins` → joint
`compile_manifests`) is the right place to catch "green in CI, dead at live
boot" wiring gaps. Landing this fence AS a `compile_manifests` pass — rather
than a standalone `tools/check_*.py` — means it inherited that entire gate
family (corpus gate + plugin-boot proof + `check_runtime_smoke`) for free, with
no new gate wiring. Guard recipe for the next such class: prefer a
`compile_manifests` pass over a bespoke checker whenever the invariant is a
pure function of the joint projected manifest set — one edit, every gate.

## Guard recipe

- Anchor: `tools/manifest_compile.py::_p3b_app_tree` (wired at the P3 boundary
  in `compile_manifests`).
- Condition source of truth: `sb/adapters/discord/command_tree.py::register_app_commands`
  (`:107-120`) + `_group_for` (`:89-102`).
- Tests: `tests/unit/compiler/test_app_tree_collision.py` (positive / negative
  #86-shape / cross-manifest joint set) + `tests/unit/app/test_plugin_host.py::TestContractFences::test_joint_compile_catches_a_slash_root_group_collision`.

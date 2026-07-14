"""P3b — the app-command-tree shape fence (tools/manifest_compile.py
``_p3b_app_tree``).

Finding #3 on PR #370 was a live-boot-only crash: a manifest declaring a
slash-capable ROOT command whose name equals a subcommand-GROUP name compiles
green in CI, then discord.py's ``tree.add_command`` raises
``CommandAlreadyRegistered`` the moment ``register_app_commands`` adds the
second claimant of that one top-level name. These tests hold the compile gate
to the EXACT condition
``sb/adapters/discord/command_tree.py::register_app_commands`` (:107-:120)
registers under — proven with the LIVE grammar (real ``CommandSpec`` /
``CommandKind``), headlessly (no discord import), so the class is caught
statically from now on.

The critical false-positive guard is ``test_prefix_only_root_...``: a
PREFIX-only root sharing a group's name is exactly how the #86 idle fix and
the in-tree G-6 ``!karma``/``/karma`` coexistence stay legal — a prefix
message never becomes an app command, so it never collides. The check MUST
leave that green.
"""

from __future__ import annotations

from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from tools.manifest_compile import COLLISION, compile_manifests


def _app_tree_hits(result) -> list:
    return [v for v in result.violations if v.pass_name == "app_tree"]


def test_slash_root_group_collision_is_rejected():
    """A slash root ``/quest`` + a subcommand group ``quest`` (slash leaf) is
    the exact CommandAlreadyRegistered shape — REJECTED with an app_tree
    COLLISION that names the offending name and points at the fix."""
    manifest = SubsystemManifest(
        key="questa",
        commands=(
            CommandSpec(name="quest", kind=CommandKind.SLASH),
            CommandSpec(name="status", kind=CommandKind.SLASH, group="quest"),
        ),
    )
    result = compile_manifests(manifests=[manifest])
    assert not result.ok
    hits = _app_tree_hits(result)
    assert len(hits) == 1, result.violations
    (v,) = hits
    assert v.failure_class == COLLISION
    assert v.locus == "command:quest"
    assert "slash_root_group_collision" in v.detail
    assert "CommandAlreadyRegistered" in v.detail
    assert "kind=prefix" in v.detail  # names the remedy


def test_both_kind_root_group_collision_is_rejected():
    """``kind=both`` is slash-capable (register_app_commands registers the
    slash half), so a BOTH root sharing a group's name collides too."""
    manifest = SubsystemManifest(
        key="questb",
        commands=(
            CommandSpec(name="quest", kind=CommandKind.BOTH),
            CommandSpec(name="status", kind=CommandKind.SLASH, group="quest"),
        ),
    )
    result = compile_manifests(manifests=[manifest])
    assert not result.ok
    hits = _app_tree_hits(result)
    assert len(hits) == 1 and hits[0].locus == "command:quest"


def test_prefix_only_root_with_same_group_name_compiles_clean():
    """THE false-positive guard (#86 idle fix / G-6 coexistence): the SAME
    names, but the root is ``kind=prefix``. A prefix message never registers
    as an app command, so register_app_commands adds no root Command under
    ``quest`` — only the Group. ZERO collision; the manifest compiles fully
    green."""
    manifest = SubsystemManifest(
        key="questc",
        commands=(
            CommandSpec(name="quest", kind=CommandKind.PREFIX),
            CommandSpec(name="status", kind=CommandKind.SLASH, group="quest"),
        ),
    )
    result = compile_manifests(manifests=[manifest])
    assert result.ok, result.violations
    assert _app_tree_hits(result) == []


def test_prefix_only_group_does_not_collide_with_a_slash_root():
    """The mirror guard (the in-tree ``karma`` shape): a slash ROOT plus a
    group whose ONLY leaf is prefix. register_app_commands never mints a Group
    node for a prefix-only family, so there is nothing to collide with the
    slash root — green."""
    manifest = SubsystemManifest(
        key="karmalike",
        commands=(
            CommandSpec(name="karma", kind=CommandKind.SLASH),          # /karma root
            CommandSpec(name="top", kind=CommandKind.PREFIX, group="karma"),  # !karma top
        ),
    )
    result = compile_manifests(manifests=[manifest])
    assert result.ok, result.violations
    assert _app_tree_hits(result) == []


def test_cross_manifest_root_group_collision_is_caught():
    """The collision is a JOINT-set property — register_app_commands builds
    ONE tree from ALL live manifests. A slash root in manifest A and a group
    of the same name in manifest B collide at live boot; the joint compile
    (the exact ``compile_manifests(manifests=host+plugins)`` call
    ``load_plugins`` makes) catches it."""
    root_manifest = SubsystemManifest(
        key="arenahost",
        commands=(CommandSpec(name="arena", kind=CommandKind.SLASH),),
    )
    group_manifest = SubsystemManifest(
        key="arenaplugin",
        commands=(CommandSpec(name="join", kind=CommandKind.SLASH, group="arena"),),
    )
    result = compile_manifests(manifests=[root_manifest, group_manifest])
    assert not result.ok
    hits = _app_tree_hits(result)
    assert len(hits) == 1
    (v,) = hits
    assert v.locus == "command:arena"
    # claimants name BOTH offending subsystems (order-independent).
    assert {v.claimant_a, v.claimant_b} == {"arenahost", "arenaplugin"}

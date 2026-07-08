"""``sb/manifest`` — pure declarations + handler registrations (design-spec §1.1).

Each module declares `MANIFEST = SubsystemManifest(...)` and binds its
callables with the `@handler`/`@panel`/`@engine`/`@workflow`/`@provider`
decorators from `sb.spec.refs`. The compiler (`tools/manifest_compile.py`)
imports every module here (P1), so declaring IS reserving (design-spec §3.2).

EMPTY at K2: subsystem manifests are authored by the port bands (Phase 4).
"""

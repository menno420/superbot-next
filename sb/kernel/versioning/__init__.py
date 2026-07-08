"""K9/S10 — the versioned-state policy kernel (frozen L0 spec 09 §3.3).

The grammar (`VersionPolicy`/`VersionedRow`/version-extended `StoreSpec`)
was authored at S5 in sb/spec/versioning.py (spec 08 §5.1 consumed it);
this package lands the load-time primitive + the compile fence:

  resolve.py — resolve_versioned_load (resume / upcast / compensate /
               reject-retire / quarantine) + run_recovery (the generated
               sweep replacing every hand-written recover_* branch)
  compile.py — the version_policy_declared fence (DROP-on-value is
               unbuildable — the RPS-forfeit shape)
"""

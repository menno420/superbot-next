"""The NEW-bot replay adapter (D-0025's named unblock; design-spec §6 gate 5).

A fake-HTTP/gateway transport over sb/'s REAL interaction pipeline that
satisfies the same driving contract as the imported old-bot harness
(`parity/harness/boot.Harness`): `start()` / `send_command` / `invoke_slash`
/ `click` / `take_calls` / `take_events` / `close`, plus a capture/replay
runner producing golden documents in the identical schema (harness_version 1,
same Normalizer, same db-delta engine).

Deterministic, network-free: ids/timestamps come from the imported harness's
own `World`/`Clock` (parity/harness/world.py — stdlib-only, reused verbatim);
DB goes through sb's K3 pool against the CI Postgres service container;
outbound effects are recorded in the old capture's wire vocabulary
(`send_message` / `interaction_response` / `followup_send` / ...) so every
diff line reads in one language.

Wired into tools/run_golden_parity.py's driver seam (`_replay_binding`).
"""

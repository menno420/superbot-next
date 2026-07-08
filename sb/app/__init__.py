"""``sb/app`` — the composition root (may import all layers).

Boot order is owned by frozen L0 spec 05 §6 (single source): preflight ->
compiler boot-gate legs -> db.init -> EventBus -> lifecycle STARTING ->
gateway connect -> on_ready -> leg C -> RUNNING -> /ready 200.
"""

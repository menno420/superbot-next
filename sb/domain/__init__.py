"""``sb/domain`` — the port-band subsystem implementations (design-spec
§9.2: `service.py` + `engine.py`/ops behind the audited seams).

Domains NEVER touch discord directly (tools/check_no_skip.py fence), never
open their own transactions around K7 ops (the engine owns the txn), and
declare every surface in their `sb/manifest/<key>.py` module. Band 1 opens
the package: settings (the platform proving itself on itself).
"""

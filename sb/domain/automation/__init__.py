"""The automation domain — the MINIMAL rule-write seam (the K9
``add_automation_rule`` apply lane; ORACLE disbot/services/
automation_mutation.py + automation_templates.py + utils/db/automation.py
@ f969b95, migration 032 → 0055_automation_rules.sql).

This slice ports ONLY the create-rule write path: the preset-referenced
template catalogue (templates.py), the ``automation_rules`` store
(store.py), and the K7 ``automation.add_rule`` op (ops.py) — rules
insert DISABLED, exactly like the oracle. The runtime consumer (the
oracle's poll-based AutomationScheduler + executor + registry + the
``automation_runs`` companion, 1,658 LOC across 4 service files) is the
NAMED SUCCESSOR: the oracle itself persists member_join rules nothing
consumes yet (no on_member_join event bridge exists there either), so
disabled rows are inert by design.
"""

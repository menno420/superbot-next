"""``sb/kernel/outbox`` — the event outbox / durable delivery (K4, spec 08).

The single durable path from "a committed DB mutation" to "its bus event
reached every subscriber": `AT_LEAST_ONCE` events are written as
`event_outbox` rows INSIDE the producer's `db.transaction()` conn (the event
exists iff the effect committed), and the post-commit `OutboxRelayLane`
delivers them to the bus with at-least-once + handler-dedup semantics.

The frozen three-part contract (spec 08 §6): enqueue = exactly-once capture ·
relay -> bus = at-least-once · effectful subscriber = idempotent on the
reserved `_outbox_dedup_key` kwarg.

Layer: kernel — imports sb/spec/events, sb/kernel/db/*, and the PollLane port
from sb/kernel/scheduler/poll; NEVER cogs/views/services. The relay/reaper
lanes are AUTHORED here (K4) and REGISTERED on the one PollSupervisor at K5
(F-1/RC-20).
"""

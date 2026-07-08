"""``sb/kernel/scheduler`` — the shared poll host (K5) + the due-queue (K9).

S5 authors `poll.py`'s PORT types (`PollLane`, `LaneTickResult`) because the
K4 outbox lanes implement them (authored-at-K4 / registered-at-K5, F-1/RC-20).
S6 (K5) adds the ONE `PollSupervisor` and spawns it in the composition root.
S10 (K9) adds `due_queue.py` / `misfire.py` and `sb/kernel/db/scheduler.py`.
"""

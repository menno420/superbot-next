"""Live process-state reads (diagnostic flip, ORDER 017 fix slice) —
the successor reads behind the Diagnostics-hub 🤖 Bot Status and
💻 System Info cards.

The capture skipped the process-state class as NONDETERMINISTIC
(parity/goldens/_sweep_skips.json), so no golden pins these bytes —
the port keeps the shipped embed SHAPE (services/diagnostic_helpers
``build_bot_status_embed`` / ``build_system_info_embed``: titles,
field names, formats verbatim) over v1's own live reads:

* CPU / RAM — the oracle used ``psutil`` (``cpu_percent(interval=1)``
  / ``virtual_memory().percent``); v1 carries no psutil dependency, so
  the same numbers come from ``/proc/stat`` (two samples, 1s apart,
  busy/total delta — psutil's own formula) and ``/proc/meminfo``
  (``(total - available) / total`` — psutil's ``percent``). A non-Linux
  host or read failure degrades to ``None`` → the card renders ``n/a``
  (never a crash, never invented numbers).
* Uptime — the process start from ``/proc/self/stat`` (field 22, clock
  ticks) against ``/proc/uptime``; fallback: this module's import time.
* Disk — ``shutil.disk_usage`` over ``/`` (the oracle's fallback branch
  when its DATA_DIR is absent — v1 has no JSON data directory, the
  validate_json guard's same truth).

Everything here is a READ of the local process/host — no Discord, no
DB, no seam to arm."""

from __future__ import annotations

import datetime
import shutil
import time

__all__ = [
    "cpu_percent",
    "disk_usage_line",
    "ram_percent",
    "uptime_text",
]

_IMPORTED_AT = time.time()


def _read_proc_stat() -> tuple[float, float] | None:
    """(busy, total) jiffies from the aggregate ``cpu`` line."""
    try:
        with open("/proc/stat", encoding="ascii") as fh:
            first = fh.readline().split()
        if first[:1] != ["cpu"]:
            return None
        fields = [float(x) for x in first[1:]]
        idle = fields[3] + (fields[4] if len(fields) > 4 else 0.0)  # idle+iowait
        total = sum(fields)
        return total - idle, total
    except Exception:  # noqa: BLE001 — a diagnostics read never raises
        return None


async def cpu_percent(interval: float = 1.0) -> float | None:
    """The psutil ``cpu_percent(interval=1)`` twin over /proc/stat —
    async sleep instead of the oracle's blocking wait."""
    import asyncio

    a = _read_proc_stat()
    if a is None:
        return None
    await asyncio.sleep(interval)
    b = _read_proc_stat()
    if b is None:
        return None
    busy = b[0] - a[0]
    total = b[1] - a[1]
    if total <= 0:
        return 0.0
    return round(busy / total * 100.0, 1)


def ram_percent() -> float | None:
    """psutil ``virtual_memory().percent`` twin over /proc/meminfo."""
    try:
        info: dict[str, float] = {}
        with open("/proc/meminfo", encoding="ascii") as fh:
            for line in fh:
                key, _, rest = line.partition(":")
                info[key.strip()] = float(rest.split()[0])
        total = info["MemTotal"]
        avail = info.get("MemAvailable")
        if avail is None or total <= 0:
            return None
        return round((total - avail) / total * 100.0, 1)
    except Exception:  # noqa: BLE001
        return None


def _process_started_at() -> float:
    """Process start (epoch seconds) from /proc/self/stat; fallback:
    this module's import time."""
    try:
        with open("/proc/self/stat", encoding="ascii") as fh:
            stat = fh.read()
        # field 22 (1-based) is starttime in clock ticks — split AFTER the
        # parenthesized comm field (which may contain spaces).
        after = stat.rpartition(")")[2].split()
        start_ticks = float(after[19])          # field 22 == after-comm idx 20
        import os
        hz = float(os.sysconf("SC_CLK_TCK"))
        with open("/proc/uptime", encoding="ascii") as fh:
            host_uptime = float(fh.read().split()[0])
        return time.time() - (host_uptime - start_ticks / hz)
    except Exception:  # noqa: BLE001
        return _IMPORTED_AT


def uptime_text() -> str:
    """The oracle's ``str(uptime_delta).split(".")[0]`` byte shape."""
    seconds = max(0.0, time.time() - _process_started_at())
    return str(datetime.timedelta(seconds=seconds)).split(".")[0]


def disk_usage_line(path: str = "/") -> str:
    """The oracle's Disk field format, verbatim
    (``build_system_info_embed``)."""
    total, used, free = shutil.disk_usage(path)
    return (f"Total: {total / 2**30:.1f} GB  "
            f"Used: {used / 2**30:.1f} GB  "
            f"Free: {free / 2**30:.1f} GB")

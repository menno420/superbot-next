#!/usr/bin/env python3
"""Plugin pin tool — write/verify ``plugins.lock.json`` (the committed pin
registry for out-of-tree game plugins; docs/game-plugin-contract.md).

  python3 tools/plugin_pin.py            # verify: installed set vs pins
  python3 tools/plugin_pin.py --write    # regenerate pins from the
                                         # INSTALLED plugin set (validates
                                         # first: facet fence + the joint
                                         # host+plugins compile)

Verify mode is exactly the boot-time ``plugin_gate`` verdict (same
``load_plugins`` call the composition root makes): an installed-but-unpinned
plugin or a hash drift is red; a pinned-but-not-installed plugin is a
warning; zero installed plugins with zero pins is vacuously green — this
tool never needs to be in the hermetic-CI fleet (CI containers install no
plugins; the boot gate enforces at runtime).

Ops CLI (never imported at runtime by the kernel; the plugin_host module is
the composition root's consumer).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sb.app.plugin_host import (  # noqa: E402
    PINS_FILENAME,
    build_pins,
    discover_plugins,
    load_plugins,
)


def _host_manifests() -> list:
    from sb.app.main import load_live_manifests

    return load_live_manifests()


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Write/verify plugins.lock.json (game-plugin pins).")
    parser.add_argument("--write", action="store_true",
                        help="regenerate the pin registry from the installed "
                             "plugin set (else verify against it)")
    parser.add_argument("--pins", default=str(_REPO_ROOT / PINS_FILENAME))
    args = parser.parse_args(argv)

    pins_path = Path(args.pins)
    host = _host_manifests()

    if args.write:
        errors: list[str] = []
        discovered = discover_plugins(errors=errors)
        for err in errors:
            print(f"plugin_pin: {err}", file=sys.stderr)
        if errors:
            return 1
        pins = build_pins(discovered)
        report = load_plugins(host, pins=pins)
        for violation in report.violations:
            print(f"plugin_pin: {violation}", file=sys.stderr)
        if report.violations:
            return 1
        pins_path.write_text(
            json.dumps(pins, sort_keys=True, indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8")
        print(f"plugin_pin: wrote {pins_path} — "
              f"{len(pins['plugins'])} plugin(s): "
              f"{', '.join(sorted(pins['plugins'])) or '(none)'}")
        return 0

    report = load_plugins(host)
    for dist_name in report.skipped:
        print(f"plugin_pin: WARNING — pinned but not installed: {dist_name}")
    for violation in report.violations:
        print(f"plugin_pin: {violation}", file=sys.stderr)
    if report.violations:
        return 1
    print(f"plugin_pin: green — {len(report.loaded)} plugin(s) admitted"
          + (f": {'; '.join(report.loaded)}" if report.loaded else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

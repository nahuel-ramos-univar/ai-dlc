#!/usr/bin/env python3
"""Write .cursor-plugin/plugin.json version."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLUGIN_JSON = REPO / ".cursor-plugin" / "plugin.json"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def apply_version(version: str, plugin_path: Path = PLUGIN_JSON) -> None:
    version = version.lstrip("v")
    if not VERSION_RE.match(version):
        raise ValueError(f"invalid version {version!r} (need X.Y.Z)")
    data = json.loads(plugin_path.read_text(encoding="utf-8"))
    data["version"] = version
    plugin_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("version", help="SemVer X.Y.Z")
    args = parser.parse_args()
    try:
        apply_version(args.version)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"• {PLUGIN_JSON.relative_to(REPO)} → {args.version.lstrip('v')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

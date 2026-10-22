#!/usr/bin/env python3
"""afterFileEdit adapter: refresh the explorer when plugin source changes.

Fails open. Never rewrites the explorer in response to an explorer edit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_aidlc_explorer import generate, payload_paths, should_refresh_path  # noqa: E402


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        print("{}")
        return 0
    try:
        if any(should_refresh_path(Path(path), ROOT) for path in payload_paths(payload)):
            generate(ROOT)
    except Exception:
        print("{}")
        return 0
    print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

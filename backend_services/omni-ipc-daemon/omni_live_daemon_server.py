#!/usr/bin/env python3
"""Redirect to the one canonical daemon (issue #6).

This folder used to hold its own v1.0.0 daemon copy, which had drifted far behind
Admin/omni_live_daemon_server.py (no signing, mesh ID, remote hub or catch-up sync).
Running this file now starts the canonical daemon with the same arguments and environment.
Edit Admin/omni_live_daemon_server.py, never this file.
"""
import runpy
import sys
from pathlib import Path

CANONICAL = Path(__file__).resolve().parents[2] / "Admin" / "omni_live_daemon_server.py"

if __name__ == "__main__":
    if not CANONICAL.is_file():
        sys.exit(f"Canonical daemon not found at {CANONICAL}")
    sys.path.insert(0, str(CANONICAL.parent))   # so it can import omni_signing / omni_negentropy
    sys.argv[0] = str(CANONICAL)
    runpy.run_path(str(CANONICAL), run_name="__main__")

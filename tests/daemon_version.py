"""The daemon's VERSION constant, read from Admin/omni_live_daemon_server.py without importing it.

Tests compare what a running daemon reports against this instead of a hard-coded string, so a
version bump no longer breaks unrelated suites (it did: test_remote_hub and test_catchup_sync still
expected 8.8.1 on an 8.12.0 daemon)."""
import re
from pathlib import Path

DAEMON_FILE = Path(__file__).resolve().parent.parent / "Admin" / "omni_live_daemon_server.py"


def daemon_version(path: Path = DAEMON_FILE) -> str:
    m = re.search(r'^VERSION = "(\d+\.\d+\.\d+)"', path.read_text(encoding="utf-8"), re.M)
    if not m:
        raise AssertionError(f"no VERSION = \"x.y.z\" line in {path}")
    return m.group(1)


DAEMON_VERSION = daemon_version()

"""Issue #7 follow-ups: no chain fork under concurrent appends, far-future events rejected,
replayed events are a no-op.

Run: python -m unittest tests/test_chain_integrity.py -v   (no daemon needed)
Imports the daemon in-process with HOME and cwd in a temp dir.
"""
import importlib
import os
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ADMIN = Path(__file__).resolve().parent.parent / "Admin"
sys.path.insert(0, str(ADMIN))

_TMP = Path(tempfile.mkdtemp(prefix="omni_chain_test_"))
os.environ["HOME"] = str(_TMP)
os.environ.pop("OMNI_TRUSTED_KEYS_FILE", None)
os.environ.pop("OMNI_LEGACY_FLOAT_TS", None)
os.environ.pop("OMNI_MAX_FUTURE_SKEW_S", None)
os.chdir(_TMP)

import omni_signing as sig  # noqa: E402
daemon = importlib.import_module("omni_live_daemon_server")  # noqa: E402
daemon.init_db()
daemon.relay_event_to_peers = lambda *a, **k: None  # no network in tests

alice = sig.load_or_create_key(_TMP / "alice.key")
ALICE = sig.pubkey_hex(alice)
_n = 0


def peer_event(ts_ms):
    global _n
    _n += 1
    ev = {"action": "CHAT", "author_pubkey": ALICE, "payload": {"t": f"hi {_n}"},
          "previous_hash": "0x" + "2" * 64, "ts": ts_ms}
    ev["signature"] = sig.sign_event(alice, ev)
    return ev


def rows():
    conn = sqlite3.connect(str(_TMP / "continuity_events.db"))
    try:
        return conn.execute("SELECT event_id, previous_hash, author_pubkey FROM events ORDER BY id").fetchall()
    finally:
        conn.close()


class ConcurrentAppendTests(unittest.TestCase):
    def test_parallel_local_appends_form_one_linear_chain(self):
        before = len(rows())
        n = 40
        barrier = threading.Barrier(n)
        results = []

        def worker(i):
            barrier.wait()
            results.append(daemon.process_and_store_event({"action": "POST", "payload": {"i": i}}))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual([s for _, s in results], [200] * n)
        new = rows()[before:]
        self.assertEqual(len(new), n)
        # Each local event chains onto the row stored right before it: no two share a parent.
        all_rows = rows()
        for idx in range(before, len(all_rows)):
            if all_rows[idx][2] == daemon.STATE.node_id:
                self.assertEqual(all_rows[idx][1], all_rows[idx - 1][0], f"fork at row {idx}")
        parents = [r[1] for r in new]
        self.assertEqual(len(parents), len(set(parents)), "two events chained onto the same head")


class FutureAndReplayTests(unittest.TestCase):
    def test_far_future_event_rejected(self):
        ev = peer_event(int((time.time() + 3600) * 1000))
        resp, status = daemon.process_and_store_event(ev, origin_peer="10.0.0.9", relay=False)
        self.assertEqual(status, 400)
        self.assertIn("future", resp["message"])

    def test_small_clock_skew_allowed(self):
        ev = peer_event(int((time.time() + 60) * 1000))
        _, status = daemon.process_and_store_event(ev, origin_peer="10.0.0.9", relay=False)
        self.assertEqual(status, 200)

    def test_old_event_still_accepted_for_catchup(self):
        ev = peer_event(int((time.time() - 30 * 86400) * 1000))
        _, status = daemon.process_and_store_event(ev, origin_peer="10.0.0.9", relay=False)
        self.assertEqual(status, 200)

    def test_replay_is_a_noop(self):
        ev = peer_event(int(time.time() * 1000))
        first, s1 = daemon.process_and_store_event(dict(ev), origin_peer="10.0.0.9", relay=False)
        count = len(rows())
        again, s2 = daemon.process_and_store_event(dict(ev), origin_peer="10.0.0.9", relay=False)
        self.assertEqual((s1, s2), (200, 200))
        self.assertEqual(again["result"], "ALREADY_EXISTS")
        self.assertEqual(again["event_id"], first["event_id"])
        self.assertEqual(len(rows()), count)

    def test_rejected_event_leaves_no_row_and_db_unlocked(self):
        ev = peer_event(int(time.time() * 1000))
        ev["signature"] = "00" * 64
        count = len(rows())
        _, status = daemon.process_and_store_event(ev, origin_peer="10.0.0.9", relay=False)
        self.assertEqual(status, 401)
        self.assertEqual(len(rows()), count)
        _, status = daemon.process_and_store_event({"action": "POST", "payload": {"after": 1}})
        self.assertEqual(status, 200)   # the rollback released the write lock


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Mesh name (OMNI_MESH_ID): /p2p/sync header check (403), UDP discovery filtering, startup validation.

Run: python -m unittest tests/test_mesh_id.py -v   (no daemon needed)
Imports the daemon module in-process with HOME and cwd pointed at a temp dir, so it never
touches ~/.omniverse or a real continuity_events.db. The sync tests run P2PSyncHandler on an
ephemeral loopback port.
"""
import importlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ADMIN = Path(__file__).resolve().parent.parent / "Admin"
sys.path.insert(0, str(ADMIN))

_PYPATH = os.pathsep.join(p for p in sys.path if p)  # keep user site-packages visible to subprocesses
_TMP = Path(tempfile.mkdtemp(prefix="omni_mesh_test_"))
os.environ["HOME"] = str(_TMP)
os.environ.pop("OMNI_TRUSTED_KEYS_FILE", None)
os.environ.pop("OMNI_LEGACY_FLOAT_TS", None)
os.environ["OMNI_MESH_ID"] = "test-mesh-1"
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.chdir(_TMP)

import omni_signing as sig  # noqa: E402
daemon = importlib.import_module("omni_live_daemon_server")  # noqa: E402
daemon.init_db()

alice = sig.load_or_create_key(_TMP / "alice.key")
ALICE = sig.pubkey_hex(alice)
_n = 0


def signed():
    global _n
    _n += 1
    ev = {"action": "CHAT", "author_pubkey": ALICE, "payload": {"t": f"mesh {_n}"},
          "previous_hash": "0x" + "1" * 64, "ts": 1793042651190 + _n}
    ev["signature"] = sig.sign_event(alice, ev)
    return ev


class SyncHeaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), daemon.P2PSyncHandler)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}/p2p/sync"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def post(self, body: bytes, mesh=None):
        headers = {"Content-Type": "application/json"}
        if mesh is not None:
            headers["X-Omni-Mesh"] = mesh
        req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=3) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, {"raw": raw[:200]}  # send_error() replies with HTML

    def count_events(self):
        import sqlite3
        conn = sqlite3.connect(str(_TMP / "continuity_events.db"))
        n = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        conn.close()
        return n

    def test_matching_mesh_accepted(self):
        code, body = self.post(json.dumps(signed()).encode(), mesh="test-mesh-1")
        self.assertEqual(code, 200, body)
        self.assertEqual(body["status"], "SUCCESS")

    def test_mismatched_mesh_403_and_not_stored(self):
        before = self.count_events()
        code, body = self.post(json.dumps(signed()).encode(), mesh="prod")
        self.assertEqual(code, 403, body)
        self.assertEqual(self.count_events(), before)

    def test_missing_header_403(self):
        code, _ = self.post(json.dumps(signed()).encode())
        self.assertEqual(code, 403)

    def test_403_comes_before_any_parsing(self):
        # A body that would be a 400 (not JSON) on the right mesh is a 403 on the wrong one.
        code, _ = self.post(b"{not json", mesh="other")
        self.assertEqual(code, 403)
        code, _ = self.post(b"{not json", mesh="test-mesh-1")
        self.assertEqual(code, 400)

    def test_signature_still_checked_on_matching_mesh(self):
        ev = signed()
        ev["payload"] = {"t": "edited"}
        code, _ = self.post(json.dumps(ev).encode(), mesh="test-mesh-1")
        self.assertEqual(code, 401)

    def test_relay_sends_mesh_header(self):
        sent = []

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        orig = daemon.urllib.request.urlopen
        daemon.urllib.request.urlopen = lambda req, timeout=None: (sent.append(req), FakeResp())[1]
        try:
            with daemon.STATE.lock:
                daemon.STATE.active_peers = {"10.9.9.9": {"ip": "10.9.9.9", "port": 5005, "last_seen": 0}}
            daemon.relay_event_to_peers(signed())
        finally:
            daemon.urllib.request.urlopen = orig
            with daemon.STATE.lock:
                daemon.STATE.active_peers = {}
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0].get_header("X-omni-mesh"), "test-mesh-1")


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        with daemon.STATE.lock:
            daemon.STATE.active_peers = {}

    def beacon(self, mesh="__omit__"):
        msg = {"type": "OMNI_P2P_BEACON", "node_id": "ab" * 32, "ip": "10.0.0.5", "port": 5005}
        if mesh != "__omit__":
            msg["mesh_id"] = mesh
        return msg

    def test_same_mesh_peer_added(self):
        self.assertTrue(daemon.handle_discovery_packet(self.beacon("test-mesh-1"), "10.0.0.5"))
        self.assertIn("10.0.0.5", daemon.STATE.active_peers)

    def test_other_mesh_ignored(self):
        self.assertFalse(daemon.handle_discovery_packet(self.beacon("prod"), "10.0.0.6"))
        self.assertNotIn("10.0.0.6", daemon.STATE.active_peers)

    def test_missing_mesh_ignored(self):
        self.assertFalse(daemon.handle_discovery_packet(self.beacon(), "10.0.0.7"))
        self.assertNotIn("10.0.0.7", daemon.STATE.active_peers)

    def test_peer_that_switches_mesh_is_dropped(self):
        daemon.handle_discovery_packet(self.beacon("test-mesh-1"), "10.0.0.8")
        daemon.handle_discovery_packet(self.beacon("prod"), "10.0.0.8")
        self.assertNotIn("10.0.0.8", daemon.STATE.active_peers)

    def test_reject_logged_once_per_peer(self):
        import io
        import contextlib
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            for _ in range(3):
                daemon.handle_discovery_packet(self.beacon("prod"), "10.0.0.9")
        self.assertEqual(out.getvalue().count("10.0.0.9"), 1)

    def test_own_beacon_ignored(self):
        msg = dict(self.beacon("test-mesh-1"), node_id=daemon.STATE.node_id)
        self.assertFalse(daemon.handle_discovery_packet(msg, "10.0.0.10"))


class MeshIdValidationTests(unittest.TestCase):
    def test_default_and_valid(self):
        self.assertEqual(daemon.load_mesh_id(""), "dev")
        self.assertEqual(daemon.load_mesh_id("prod"), "prod")
        self.assertEqual(daemon.load_mesh_id("a" * 32), "a" * 32)
        self.assertEqual(daemon.load_mesh_id("eu-west-2"), "eu-west-2")

    def test_invalid_values_raise(self):
        for bad in ("Prod", "a" * 33, "dev mesh", "dev_1", "mesh!", "dév"):
            with self.assertRaises(ValueError, msg=bad):
                daemon.load_mesh_id(bad)

    def test_daemon_refuses_to_start_with_invalid_mesh(self):
        env = dict(os.environ, OMNI_MESH_ID="Not_Valid", HOME=str(_TMP), PYTHONPATH=_PYPATH)
        r = subprocess.run([sys.executable, "-c", "import omni_live_daemon_server"],
                           cwd=str(ADMIN), env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("OMNI_MESH_ID", r.stderr)

    def test_telemetry_reports_mesh_id(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), daemon.TelemetryHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/api/v1/telemetry/node-health"
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(url, timeout=3) as r:
                self.assertEqual(json.loads(r.read())["mesh_id"], "test-mesh-1")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)

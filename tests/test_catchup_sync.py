"""Catch-up sync (daemon v8.8.0): negentropy reconciliation between two live daemons.

Run: python -m unittest tests/test_catchup_sync.py -v

TwoDaemonCatchupTest starts two real daemons as subprocesses from temp copies of Admin/ with the
ports rewritten (A: 19100/15000/15005/19101, B: 29100/25000/25005/29101), each with its own HOME
(node key) and working dir (continuity_events.db), and OMNI_SYNC_PEERS pointing at each other.
It takes B offline, posts to A, brings B back and checks B catches up to exactly A's set, every
event verified; then plants tampered events on A and checks B rejects them.
GateTests imports the daemon in-process (HOME/cwd in a temp dir) for the access rules.
"""
import hashlib
import importlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ADMIN = Path(__file__).resolve().parent.parent / "Admin"
sys.path.insert(0, str(ADMIN))
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
_PYPATH = os.pathsep.join(p for p in sys.path if p)

import omni_signing as sig  # noqa: E402

MESH = "catchup-test"
PORTS = {
    "A": {"TELEMETRY_PORT": 19100, "CONTINUITY_IPC_PORT": 15000, "P2P_SYNC_PORT": 15005, "UDP_DISCOVERY_PORT": 19101},
    "B": {"TELEMETRY_PORT": 29100, "CONTINUITY_IPC_PORT": 25000, "P2P_SYNC_PORT": 25005, "UDP_DISCOVERY_PORT": 29101},
}
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _http(url, data=None, headers=None, timeout=60):
    body = json.dumps(data).encode() if data is not None else None
    h = dict(headers or {})
    if body is not None:
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=h, method="POST" if body is not None else "GET")
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:200]}


def _event_hash(ev: dict) -> str:
    return "0x" + hashlib.sha256(sig.canonical_event_bytes(ev)).hexdigest()


class Node:
    def __init__(self, name, root: Path, peer_port: int):
        self.name, self.ports = name, PORTS[name]
        self.code = root / f"code_{name}"
        self.home = root / f"home_{name}"
        self.cwd = root / f"run_{name}"
        for d in (self.code, self.home, self.cwd):
            d.mkdir(parents=True)
        for f in ("omni_live_daemon_server.py", "omni_signing.py", "omni_negentropy.py"):
            shutil.copy(ADMIN / f, self.code / f)
        src = (self.code / "omni_live_daemon_server.py").read_text()
        for const, port in self.ports.items():
            src, n = re.subn(rf"^{const} = \d+$", f"{const} = {port}", src, flags=re.M)
            assert n == 1, const
        (self.code / "omni_live_daemon_server.py").write_text(src)
        self.env = dict(os.environ, HOME=str(self.home), OMNI_MESH_ID=MESH, PYTHONPATH=_PYPATH,
                        OMNI_SYNC_PEERS=f"127.0.0.1:{peer_port}", OMNI_CATCHUP_STARTUP_DELAY="1",
                        OMNI_CATCHUP_INTERVAL="0", NO_PROXY="127.0.0.1,localhost")
        for k in ("OMNI_TRUSTED_KEYS_FILE", "OMNI_LEGACY_FLOAT_TS", "OMNI_HUB_REMOTE", "OMNI_HUB_BIND"):
            self.env.pop(k, None)
        self.proc = None

    @property
    def ipc(self):
        return f"http://127.0.0.1:{self.ports['CONTINUITY_IPC_PORT']}"

    @property
    def p2p(self):
        return f"http://127.0.0.1:{self.ports['P2P_SYNC_PORT']}"

    @property
    def db(self):
        return self.cwd / "continuity_events.db"

    def start(self):
        self.log = open(self.cwd / "daemon.log", "a")
        self.proc = subprocess.Popen([sys.executable, str(self.code / "omni_live_daemon_server.py")],
                                     cwd=self.cwd, env=self.env, stdout=self.log, stderr=subprocess.STDOUT)
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                code, body = _http(f"http://127.0.0.1:{self.ports['TELEMETRY_PORT']}/api/v1/telemetry/node-health", timeout=2)
                if code == 200:
                    self.node_id = body["node_id"]
                    return body
            except Exception:
                pass
            time.sleep(0.2)
        raise AssertionError(f"daemon {self.name} did not start:\n" + (self.cwd / "daemon.log").read_text()[-2000:])

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(10)
        self.proc = None
        self.log.close()

    def health(self):
        return _http(f"http://127.0.0.1:{self.ports['TELEMETRY_PORT']}/api/v1/telemetry/node-health")[1]

    def post(self, text):
        code, body = _http(f"{self.ipc}/api/events/append", {"action": "CHAT", "payload": {"text": text}})
        assert code == 200, body
        return body["event_id"]

    def catchup(self):
        return _http(f"{self.ipc}/api/sync/catchup", {})

    def rows(self):
        conn = sqlite3.connect(str(self.db))
        try:
            return conn.execute("SELECT event_id, action, author_pubkey, previous_hash, timestamp, "
                                "payload_json, signature, ts_ms FROM events").fetchall()
        finally:
            conn.close()

    def ids(self):
        return {r[0] for r in self.rows()}

    def signed_ids(self):
        return {r[0] for r in self.rows() if r[6]}

    def all_signed_verify(self):
        """Every signed row: content hash == event_id and Ed25519 signature valid."""
        bad = []
        for eid, action, author, prev, timestamp, payload_json, signature, ts_ms in self.rows():
            if not signature:
                continue
            ev = {"action": action, "author_pubkey": author, "payload": json.loads(payload_json),
                  "previous_hash": prev, **({"ts": ts_ms} if ts_ms is not None else {"timestamp": timestamp})}
            if _event_hash(ev) != eid or not sig.verify_event(dict(ev, signature=signature)):
                bad.append(eid)
        return bad


def _wait(pred, timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return True
        time.sleep(0.25)
    return pred()


class TwoDaemonCatchupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp(prefix="omni_catchup_test_"))
        cls.A = Node("A", cls.root, PORTS["B"]["P2P_SYNC_PORT"])
        cls.B = Node("B", cls.root, PORTS["A"]["P2P_SYNC_PORT"])
        cls.A.start()
        cls.B.start()
        time.sleep(1.5)   # let the startup catch-up runs (empty sets) finish

    @classmethod
    def tearDownClass(cls):
        for n in (cls.A, cls.B):
            try:
                n.stop()
            except Exception:
                pass

    def test_catchup_flow(self):
        A, B = self.A, self.B
        stats_log = {}

        # 1. Both online, nothing relays on loopback: a manual catch-up is bidirectional.
        a_first = [A.post(f"a-{i}") for i in range(3)]
        b_first = [B.post(f"b-{i}") for i in range(2)]
        code, run = B.catchup()
        self.assertEqual(code, 200, run)
        s = run["peers"][0]
        stats_log["bidirectional"] = s
        self.assertIsNone(s["error"])
        self.assertEqual((s["need"], s["stored"], s["have"], s["pushed"], s["rejected"]), (3, 3, 2, 2, 0))
        self.assertEqual(A.signed_ids(), B.signed_ids())
        self.assertTrue(set(a_first + b_first) <= B.signed_ids())

        # 2. B offline; A gets 50 new events; B comes back and catches up on its own (startup run).
        B.stop()
        posted = [A.post(f"while-B-was-away-{i}") for i in range(50)]
        self.assertFalse(set(posted) & B.signed_ids())
        B.start()
        self.assertTrue(_wait(lambda: B.signed_ids() == A.signed_ids()),
                        f"B has {len(B.signed_ids())} signed events, A has {len(A.signed_ids())}")
        self.assertEqual(B.signed_ids(), A.signed_ids())
        self.assertEqual(B.ids(), A.ids())            # incl. each node's own unsigned genesis row
        self.assertEqual(B.all_signed_verify(), [])
        self.assertEqual(A.all_signed_verify(), [])
        self.assertTrue(_wait(lambda: (B.health().get("catchup") or {}).get("peers")))
        s = B.health()["catchup"]["peers"][0]
        stats_log["reconnect"] = s
        self.assertEqual((s["need"], s["stored"], s["rejected"], s["have"]), (50, 50, 0, 0))
        self.assertLessEqual(s["rounds"], 3)
        # Feed on B reports every one of them as verified.
        code, feed = _http(f"{B.ipc}/api/events/feed?limit=200")
        self.assertEqual(code, 200)
        self.assertTrue(all(e["verified"] for e in feed["events"] if e["signature"]))

        # 3. Tampered events on A must be rejected by B, the good ones still arrive.
        B.stop()
        good = [A.post(f"good-{i}") for i in range(3)]
        victim = A.post("will be tampered")
        conn = sqlite3.connect(str(A.db))
        conn.execute("UPDATE events SET payload_json = ? WHERE event_id = ?",
                     (json.dumps({"text": "tampered after signing"}), victim))
        # Correct content hash, but the signature is from a different key than author_pubkey.
        mallory = sig.load_or_create_key(self.root / "mallory.key")
        ts = sig.now_ms()
        forged_ev = {"action": "CHAT", "author_pubkey": A.node_id, "payload": {"text": "forged"},
                     "previous_hash": "0x" + "2" * 64, "ts": ts}
        forged = _event_hash(forged_ev)
        conn.execute("INSERT INTO events (event_id, action, author_pubkey, previous_hash, timestamp, payload_json, "
                     "signature, ts_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (forged, "CHAT", A.node_id, forged_ev["previous_hash"], ts / 1000.0,
                      json.dumps(forged_ev["payload"]), sig.sign_event(mallory, forged_ev), ts))
        # A validly signed event stored under an id that is not its content hash.
        row = conn.execute("SELECT action, author_pubkey, previous_hash, timestamp, payload_json, signature, ts_ms "
                           "FROM events WHERE event_id = ?", (good[0],)).fetchone()
        wrong_id = "0x" + hashlib.sha256(b"not the content hash").hexdigest()
        conn.execute("INSERT INTO events (event_id, action, author_pubkey, previous_hash, timestamp, payload_json, "
                     "signature, ts_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (wrong_id, *row))
        conn.commit()
        conn.close()
        bad = {victim, forged, wrong_id}

        B.start()
        self.assertTrue(_wait(lambda: set(good) <= B.signed_ids()), "good events did not arrive")
        self.assertTrue(_wait(lambda: (B.health().get("catchup") or {}).get("peers")))
        s = B.health()["catchup"]["peers"][0]
        stats_log["tampered"] = s
        self.assertEqual((s["need"], s["stored"], s["rejected"]), (6, 3, 3), s)
        self.assertFalse(bad & B.signed_ids())
        self.assertEqual(B.signed_ids(), A.signed_ids() - bad)
        self.assertEqual(B.all_signed_verify(), [])
        # A second run tries again and still stores nothing bad.
        code, run = B.catchup()
        s = run["peers"][0]
        self.assertEqual((s["need"], s["stored"], s["rejected"]), (3, 0, 3), s)
        self.assertFalse(bad & B.signed_ids())
        log_b = (B.cwd / "daemon.log").read_text()
        self.assertIn("hash mismatch", log_b)
        self.assertIn("(401: Invalid or missing signature)", log_b)

        # 4. Endpoint rules: mesh header required, bad input 400.
        msg = {"negentropy": "61"}
        self.assertEqual(_http(f"{A.p2p}/p2p/reconcile", msg)[0], 403)
        self.assertEqual(_http(f"{A.p2p}/p2p/reconcile", msg, {"X-Omni-Mesh": "other"})[0], 403)
        self.assertEqual(_http(f"{A.p2p}/p2p/events", {"ids": []})[0], 403)
        self.assertEqual(_http(f"{A.p2p}/p2p/reconcile", {"negentropy": "zz"}, {"X-Omni-Mesh": MESH})[0], 400)
        self.assertEqual(_http(f"{A.p2p}/p2p/events", {"ids": ["x"] * 201}, {"X-Omni-Mesh": MESH})[0], 400)
        code, ok = _http(f"{A.p2p}/p2p/reconcile", msg, {"X-Omni-Mesh": MESH})
        self.assertEqual((code, ok["negentropy"]), (200, "61"))

        print("\n[catch-up stats] " + json.dumps(stats_log), file=sys.stderr)


class GateTests(unittest.TestCase):
    """Access rules, in-process (no sockets)."""

    @classmethod
    def setUpClass(cls):
        tmp = Path(tempfile.mkdtemp(prefix="omni_catchup_gate_"))
        cls._saved = (os.environ.get("HOME"), os.getcwd())
        os.environ["HOME"] = str(tmp)
        os.environ["OMNI_MESH_ID"] = MESH
        os.environ["OMNI_SYNC_PEERS"] = "100.64.0.7:5005,localhost"
        os.environ.pop("OMNI_HUB_REMOTE", None)
        os.chdir(tmp)
        sys.modules.pop("omni_live_daemon_server", None)
        cls.d = importlib.import_module("omni_live_daemon_server")

    @classmethod
    def tearDownClass(cls):
        home, cwd = cls._saved
        if home is not None:
            os.environ["HOME"] = home
        os.chdir(cwd)
        os.environ.pop("OMNI_SYNC_PEERS", None)

    def test_version(self):
        self.assertEqual(self.d.VERSION, "8.8.1")

    def test_parse_sync_peers(self):
        p = self.d.parse_sync_peers
        self.assertEqual(p(""), [])
        self.assertEqual(p("100.64.0.7:5005, laptop.tail1234.ts.net"),
                         [("100.64.0.7", 5005), ("laptop.tail1234.ts.net", self.d.P2P_SYNC_PORT)])
        for bad in ("host:0", "host:99999", "host:abc", "bad host"):
            with self.assertRaises(ValueError):
                p(bad)

    def test_catchup_endpoints_only_for_known_peers(self):
        d = self.d
        self.assertTrue(d.catchup_peer_allowed("127.0.0.1"))
        self.assertTrue(d.catchup_peer_allowed("100.64.0.7"))        # OMNI_SYNC_PEERS
        self.assertFalse(d.catchup_peer_allowed("10.9.9.9"))         # stranger
        with d.STATE.lock:
            d.STATE.active_peers["10.9.9.9"] = {"ip": "10.9.9.9", "port": 5005, "last_seen": time.time()}
        self.assertTrue(d.catchup_peer_allowed("10.9.9.9"))          # discovered on our mesh
        with d.STATE.lock:
            d.STATE.active_peers["10.9.9.9"]["last_seen"] = time.time() - 60
        self.assertFalse(d.catchup_peer_allowed("10.9.9.9"))         # stale
        with d.STATE.lock:
            d.STATE.active_peers.clear()

    def test_manual_trigger_is_loopback_only(self):
        self.assertNotIn("/api/sync/catchup", self.d.REMOTE_POST_PATHS)
        self.assertNotIn("/p2p/reconcile", self.d.REMOTE_POST_PATHS)

    def test_discovery_of_new_peer_wakes_catchup(self):
        d = self.d
        d.STATE.catchup_wake.clear()
        d.handle_discovery_packet({"type": "OMNI_P2P_BEACON", "node_id": "f" * 64, "mesh_id": MESH,
                                   "port": 5005}, "10.1.2.3")
        self.assertTrue(d.STATE.catchup_wake.is_set())
        d.STATE.catchup_wake.clear()
        d.handle_discovery_packet({"type": "OMNI_P2P_BEACON", "node_id": "f" * 64, "mesh_id": MESH,
                                   "port": 5005}, "10.1.2.3")
        self.assertFalse(d.STATE.catchup_wake.is_set())              # same peer again: no new run
        with d.STATE.lock:
            d.STATE.active_peers.clear()


if __name__ == "__main__":
    unittest.main()

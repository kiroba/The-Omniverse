"""Real two-node signed mesh test (issue #2). Replaces the old single-host test_v85_mesh.py.

Run: python -m unittest tests/test_two_node_mesh.py -v

Starts two real daemon processes on one machine. Each has its own HOME (so its own Ed25519 node
key), its own working dir (its own continuity_events.db) and its own ports (OMNI_*_PORT). Each
lists the other in OMNI_SYNC_PEERS, with catch-up every second. The test then checks:
  1. Each node signs its own local posts (author = its node key, feed says verified).
  2. Both logs converge: the same event-id set, so the same Merkle root over the sorted ids.
  3. A post made while the peer is down reaches it after the peer restarts (reconnect catch-up).
  4. A forged event (signed by the wrong key) pushed to node A is rejected and never reaches B.
"""
import hashlib
import json
import os
import shutil
import site
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAEMON = ROOT / "Admin" / "omni_live_daemon_server.py"
sys.path.insert(0, str(ROOT / "Admin"))
import omni_signing as sig  # noqa: E402

MESH = "two-node-test"
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def free_port(kind=socket.SOCK_STREAM):
    s = socket.socket(socket.AF_INET, kind)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def http(method, url, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with _OPENER.open(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


class Node:
    def __init__(self, name, root):
        self.name = name
        self.dir = root / name
        self.dir.mkdir()
        self.ipc, self.tel, self.p2p = free_port(), free_port(), free_port()
        self.udp = free_port(socket.SOCK_DGRAM)
        self.proc = None
        self.peer_p2p = None

    def env(self):
        env = dict(os.environ)
        for k in ("OMNI_TRUSTED_KEYS_FILE", "OMNI_HUB_REMOTE", "OMNI_HUB_BIND", "OMNI_LEGACY_FLOAT_TS"):
            env.pop(k, None)
        # A per-node HOME hides user site-packages, so pass them on explicitly (cryptography).
        extra = [p for p in [site.getusersitepackages()] if p and os.path.isdir(p)]
        env["PYTHONPATH"] = os.pathsep.join(extra + [str(DAEMON.parent)] + [env.get("PYTHONPATH", "")])
        env.update({
            "HOME": str(self.dir), "USERPROFILE": str(self.dir), "PYTHONUTF8": "1",
            "NO_PROXY": "*", "no_proxy": "*", "OMNI_MESH_ID": MESH,
            "OMNI_IPC_PORT": str(self.ipc), "OMNI_TELEMETRY_PORT": str(self.tel),
            "OMNI_P2P_PORT": str(self.p2p), "OMNI_UDP_PORT": str(self.udp),
            "OMNI_SYNC_PEERS": f"127.0.0.1:{self.peer_p2p}", "OMNI_CATCHUP_INTERVAL": "1",
        })
        return env

    def start(self):
        self.log = open(self.dir / "daemon.log", "ab")
        self.proc = subprocess.Popen([sys.executable, str(DAEMON)], cwd=str(self.dir), env=self.env(),
                                     stdout=self.log, stderr=subprocess.STDOUT)
        deadline = time.time() + 20
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"{self.name} exited:\n" + (self.dir / "daemon.log").read_text(errors="replace"))
            try:
                if http("GET", f"http://127.0.0.1:{self.ipc}/api/events/feed?limit=1")[0] == 200:
                    return
            except OSError:
                pass
            time.sleep(0.2)
        raise RuntimeError(f"{self.name} did not come up")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if getattr(self, "log", None):
            self.log.close()

    def post(self, payload):
        status, body = http("POST", f"http://127.0.0.1:{self.ipc}/api/events/append",
                            {"action": "CREATOR_POST_PUBLISHED", "payload": payload})
        assert status == 200, body
        return body["event_id"]

    def feed(self):
        return http("GET", f"http://127.0.0.1:{self.ipc}/api/events/feed?limit=200")[1]

    def ids(self):
        return {e["event_id"] for e in self.feed()["events"]}

    def merkle_root(self):
        return hashlib.sha256("".join(sorted(self.ids())).encode()).hexdigest()


def wait_for(pred, timeout=30, msg="condition"):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return
        time.sleep(0.3)
    raise AssertionError(f"timed out waiting for {msg}")


class TwoNodeMeshTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp(prefix="omni_two_node_"))
        cls.a, cls.b = Node("nodeA", cls.root), Node("nodeB", cls.root)
        cls.a.peer_p2p, cls.b.peer_p2p = cls.b.p2p, cls.a.p2p
        cls.a.start()
        cls.b.start()

    @classmethod
    def tearDownClass(cls):
        cls.a.stop()
        cls.b.stop()
        shutil.rmtree(cls.root, ignore_errors=True)

    def test_1_nodes_have_distinct_keys_and_sign_their_posts(self):
        ea = self.a.post({"title": "from A"})
        eb = self.b.post({"title": "from B"})
        fa, fb = self.a.feed(), self.b.feed()
        self.assertNotEqual(fa["node_id"], fb["node_id"])
        mine_a = next(e for e in fa["events"] if e["event_id"] == ea)
        mine_b = next(e for e in fb["events"] if e["event_id"] == eb)
        self.assertEqual(mine_a["author_pubkey"], fa["node_id"])
        self.assertEqual(mine_b["author_pubkey"], fb["node_id"])
        self.assertTrue(mine_a["verified"] and mine_b["verified"])

    def test_2_logs_converge_to_same_merkle_root(self):
        posted = {self.a.post({"n": i, "from": "A"}) for i in range(5)}
        posted |= {self.b.post({"n": i, "from": "B"}) for i in range(5)}
        wait_for(lambda: posted <= self.a.ids() and posted <= self.b.ids(), msg="both nodes to hold all posts")
        wait_for(lambda: self.a.ids() == self.b.ids(), msg="identical event sets")
        self.assertEqual(self.a.merkle_root(), self.b.merkle_root())
        # Events B received from A keep A's signature and still verify on B.
        fb = self.b.feed()
        from_a = [e for e in fb["events"] if e["author_pubkey"] == self.a.feed()["node_id"]
                  and e["action"] != "GENESIS_NODE_INIT"]
        self.assertTrue(from_a)
        self.assertTrue(all(e["verified"] for e in from_a))

    def test_3_reconnect_catch_up(self):
        self.b.stop()
        missed = {self.a.post({"while_b_down": i}) for i in range(10)}
        self.b.start()
        wait_for(lambda: missed <= self.b.ids(), msg="B to catch up after restart")
        wait_for(lambda: self.a.ids() == self.b.ids(), msg="identical sets after reconnect")

    def test_4_forged_event_rejected_and_not_propagated(self):
        alice = sig.load_or_create_key(self.root / "alice.key")
        mallory = sig.load_or_create_key(self.root / "mallory.key")
        ev = {"action": "CHAT", "author_pubkey": sig.pubkey_hex(alice), "payload": {"t": "forged"},
              "previous_hash": "0x" + "3" * 64, "ts": sig.now_ms()}
        ev["signature"] = sig.sign_event(mallory, ev)
        status, _ = http("POST", f"http://127.0.0.1:{self.a.p2p}/p2p/sync", ev, {"X-Omni-Mesh": MESH})
        self.assertEqual(status, 401)
        time.sleep(2.5)   # two catch-up rounds
        for node in (self.a, self.b):
            self.assertFalse(any(e["payload"].get("t") == "forged" for e in node.feed()["events"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)

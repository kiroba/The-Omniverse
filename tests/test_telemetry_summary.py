"""Telemetry summary (daemon v8.12.0): GET :5000/api/telemetry/summary for the Mesh Monitor app.

Run: python -m unittest tests/test_telemetry_summary.py -v
Starts real daemons as subprocesses on free temp ports (OMNI_*_PORT overrides), with HOME and cwd in
temp dirs, like tests/test_signal_mailbox.py. OMNI_TELEMETRY_CACHE_S=0 so every request re-reads the
store. The remote-hub test talks to this machine's non-loopback IP and is skipped without one.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent.parent
ADMIN = ROOT / "Admin"
sys.path.insert(0, str(ADMIN))
from omni_signing import canonical_event_bytes  # noqa: E402  (pure function, no key files touched)

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_PYPATH = os.pathsep.join(p for p in [os.environ.get("PYTHONPATH", ""), str(ADMIN)] if p)
TURN_SECRET = "telemetry-test-secret-not-real"
FEE_BPS = 250


def _free_port(kind=socket.SOCK_STREAM) -> int:
    with socket.socket(socket.AF_INET, kind) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def _http(url, data=None, headers=None, timeout=10):
    body = json.dumps(data).encode() if data is not None else None
    h = dict(headers or {})
    if body is not None:
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=h, method="POST" if body is not None else "GET")
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, json.loads(raw), raw.decode()
    except urllib.error.HTTPError as e:
        txt = e.read()
        try:
            return e.code, json.loads(txt), txt.decode()
        except ValueError:
            return e.code, {"raw": txt[:200]}, txt.decode(errors="replace")


_last_ts = [0]
_ts_lock = threading.Lock()


def _fresh_ts() -> int:
    with _ts_lock:
        t = max(time.time_ns() // 1_000_000, _last_ts[0] + 1)
        _last_ts[0] = t
        return t


class Key:
    def __init__(self):
        self.sk = Ed25519PrivateKey.generate()
        self.pub = self.sk.public_key().public_bytes(serialization.Encoding.Raw,
                                                     serialization.PublicFormat.Raw).hex()

    def sign(self, data: bytes) -> str:
        return self.sk.sign(data).hex()

    def event(self, payload: dict, action="USER_POST") -> dict:
        ev = {"action": action, "author_pubkey": self.pub, "payload": payload,
              "previous_hash": "0x" + "1" * 64, "ts": _fresh_ts()}
        ev["signature"] = self.sign(canonical_event_bytes(ev))
        return ev


def signal_msg(sender: Key, to: str, payload="v=0\r\nSECRET-SDP-MARKER\r\n") -> dict:
    m = {"to": to, "from": sender.pub, "call_id": "call-t", "kind": "offer", "payload": payload, "ts": _fresh_ts()}
    canon = json.dumps({"type": "omnicast.signal.v1", **{k: m[k] for k in ("to", "from", "call_id", "kind",
                                                                         "payload", "ts")}},
                       sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    m["sig"] = sender.sign(canon)
    return m


class Daemon:
    def __init__(self, root: Path, name: str, remote: bool = False, turn: bool = False):
        self.home, self.cwd = root / f"home_{name}", root / f"run_{name}"
        self.home.mkdir(parents=True)
        self.cwd.mkdir(parents=True)
        self.mesh = f"tel-{name}"
        self.ports = {"OMNI_TELEMETRY_PORT": _free_port(), "OMNI_IPC_PORT": _free_port(),
                      "OMNI_P2P_PORT": _free_port(), "OMNI_UDP_PORT": _free_port(socket.SOCK_DGRAM)}
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home), PYTHONPATH=_PYPATH,
                        OMNI_MESH_ID=self.mesh, OMNI_CATCHUP_INTERVAL="0", OMNI_CATCHUP_STARTUP_DELAY="3600",
                        NO_PROXY="*", OMNI_TELEMETRY_CACHE_S="0", OMNI_TREASURY_FEE_BPS=str(FEE_BPS),
                        **{k: str(v) for k, v in self.ports.items()})
        for k in ("OMNI_TRUSTED_KEYS_FILE", "OMNI_LEGACY_FLOAT_TS", "OMNI_SYNC_PEERS", "OMNI_HUB_TOKEN_FILE",
                  "OMNI_HUB_REMOTE", "OMNI_HUB_BIND", "OMNI_TURN_URLS", "OMNI_TURN_SECRET", "OMNI_STUN_URLS",
                  "OMNI_TURN_TTL", "OMNI_REQUIRE_SIGNED_BEACONS"):
            self.env.pop(k, None)
        if remote:
            self.env.update(OMNI_HUB_REMOTE="1", OMNI_HUB_BIND="0.0.0.0")
        if turn:
            self.env.update(OMNI_TURN_URLS="turn:100.101.102.103:3478?transport=udp", OMNI_TURN_SECRET=TURN_SECRET)
        self.ipc = f"http://127.0.0.1:{self.ports['OMNI_IPC_PORT']}"
        self.p2p = f"http://127.0.0.1:{self.ports['OMNI_P2P_PORT']}"

    def start(self):
        self.log = open(self.cwd / "daemon.log", "a")
        self.proc = subprocess.Popen([sys.executable, str(ADMIN / "omni_live_daemon_server.py")], cwd=self.cwd,
                                     env=self.env, stdout=self.log, stderr=subprocess.STDOUT)
        url = f"http://127.0.0.1:{self.ports['OMNI_TELEMETRY_PORT']}/api/v1/telemetry/node-health"
        deadline = time.time() + 20
        while time.time() < deadline:
            if self.proc.poll() is not None:
                break
            try:
                code, body, _ = _http(url, timeout=2)
                if code == 200:
                    self.node_id, self.version = body["node_id"], body["version"]
                    return
            except Exception:
                pass
            time.sleep(0.2)
        self.stop()
        raise AssertionError("daemon did not start:\n" + (self.cwd / "daemon.log").read_text()[-2000:])

    def stop(self):
        if getattr(self, "proc", None) and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if getattr(self, "log", None):
            self.log.close()

    def summary(self, base=None, **kw):
        return _http(f"{base or self.ipc}/api/telemetry/summary", **kw)

    def proto(self, summary: dict, pid: str) -> dict:
        return next(p for p in summary["protocols"] if p["id"] == pid)


class TelemetrySummaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_telemetry_"))
        cls.d = Daemon(cls.tmp, "local")
        cls.d.start()

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_version_and_shape(self):
        self.assertEqual(self.d.version, "8.12.0")
        code, s, _ = self.d.summary()
        self.assertEqual(code, 200, s)
        self.assertEqual((s["status"], s["schema"], s["version"]), ("OK", 1, "8.12.0"))
        for section in ("protocols", "security", "finance", "users", "services"):
            self.assertIn(section, s)
        ids = [p["id"] for p in s["protocols"]]
        self.assertEqual(ids, ["tcp_api", "p2p_sync", "udp_discovery", "negentropy", "signaling", "turn"])
        for p in s["protocols"]:
            self.assertIn("state", p)
            self.assertIn("last_seen_ago_s", p)
        self.assertEqual(s["services"]["daemon_version"], "8.12.0")
        self.assertEqual(s["services"]["node_id_prefix"], self.d.node_id[:12])
        self.assertGreater(s["services"]["event_store"]["total_events"], 0)   # genesis
        self.assertEqual(self.d.proto(s, "turn")["configured"], False)
        self.assertEqual(self.d.proto(s, "negentropy")["state"], "idle")      # no run yet (interval 0)
        self.assertEqual(self.d.proto(s, "tcp_api")["listen"], ["127.0.0.1"])

    def test_rejects_parameters(self):
        code, body, _ = _http(f"{self.d.ipc}/api/telemetry/summary?limit=5")
        self.assertEqual(code, 400, body)

    def test_local_and_peer_event_counts(self):
        _, before, _ = self.d.summary()
        code, r, _ = _http(f"{self.d.ipc}/api/events/append", {"action": "USER_POST", "payload": {"text": "hi"}})
        self.assertEqual(code, 200, r)
        alice, mallory = Key(), Key()
        good = alice.event({"text": "PEER-PAYLOAD-MARKER"})
        hdr = {"X-Omni-Mesh": self.d.mesh}
        self.assertEqual(_http(f"{self.d.p2p}/p2p/sync", good, hdr)[0], 200)
        self.assertEqual(_http(f"{self.d.p2p}/p2p/sync", good, hdr)[0], 200)          # duplicate
        forged = dict(alice.event({"text": "x"}), signature=mallory.sign(b"not the event"))
        self.assertEqual(_http(f"{self.d.p2p}/p2p/sync", forged, hdr)[0], 401)
        self.assertEqual(_http(f"{self.d.p2p}/p2p/sync", good, {"X-Omni-Mesh": "other"})[0], 403)

        code, s, raw = self.d.summary()
        sec, b = s["security"], before["security"]
        self.assertEqual(sec["events_stored_local_signed"] - b["events_stored_local_signed"], 1)
        self.assertEqual(sec["events_verified_from_peers"] - b["events_verified_from_peers"], 1)
        self.assertEqual(sec["events_duplicate"] - b["events_duplicate"], 1)
        self.assertEqual(sec["events_rejected_signature"] - b["events_rejected_signature"], 1)
        self.assertIsNotNone(sec["last_signature_reject_ago_s"])
        p2p, bp = self.d.proto(s, "p2p_sync"), self.d.proto(before, "p2p_sync")
        self.assertEqual(p2p["counts"]["rejected_mesh"] - bp["counts"]["rejected_mesh"], 1)
        self.assertGreaterEqual(p2p["counts"]["requests"] - bp["counts"]["requests"], 3)
        self.assertIsNotNone(p2p["last_seen_ago_s"])
        # users: alice's key counts as an identity active now; the node's own key is excluded
        self.assertGreaterEqual(s["users"]["identities_seen"], before["users"]["identities_seen"] + 1)
        self.assertGreaterEqual(s["users"]["active_24h"], 1)
        self.assertGreaterEqual(s["users"]["active_7d"], s["users"]["active_24h"])
        # privacy: no full keys, no payload text
        self.assertNotIn(alice.pub, raw)
        self.assertNotIn(self.d.node_id, raw)
        self.assertNotIn("PEER-PAYLOAD-MARKER", raw)

    def test_signal_counts_without_contents(self):
        _, before, _ = self.d.summary()
        alice, bob = Key(), Key()
        ok = signal_msg(alice, bob.pub)
        self.assertEqual(_http(f"{self.d.ipc}/api/signal/send", ok)[0], 200)
        bad = dict(signal_msg(alice, bob.pub), payload="tampered SECRET-SDP-MARKER")
        self.assertEqual(_http(f"{self.d.ipc}/api/signal/send", bad)[0], 401)
        code, s, raw = self.d.summary()
        sig, bsig = self.d.proto(s, "signaling"), self.d.proto(before, "signaling")
        self.assertEqual(sig["counts"]["sends_ok"] - bsig["counts"]["sends_ok"], 1)
        self.assertEqual(sig["counts"]["sends_rejected"] - bsig["counts"]["sends_rejected"], 1)
        self.assertGreaterEqual(sig["queued"], 1)
        self.assertEqual(s["security"]["signal_sends_rejected"] - before["security"]["signal_sends_rejected"], 1)
        self.assertGreaterEqual(s["security"]["signal_sends_rejected_by_status"].get("401", 0), 1)
        self.assertNotIn("SECRET-SDP-MARKER", raw)
        self.assertNotIn(bob.pub, raw)

    def test_bug_report_count(self):
        _, before, _ = self.d.summary()
        code, r, _ = _http(f"{self.d.ipc}/api/bugs/report", {"what_happened": "BUG-TEXT-MARKER crashed"})
        self.assertEqual(code, 200, r)
        _, s, raw = self.d.summary()
        self.assertEqual(s["users"]["bug_reports"] - before["users"]["bug_reports"], 1)
        self.assertNotIn("BUG-TEXT-MARKER", raw)

    def test_finance_totals_from_ledger(self):
        _, before, _ = self.d.summary()
        f0 = before["finance"]
        self.assertEqual((f0["state"], f0["test_only"], f0["treasury_fee_bps"]), ("ok", True, FEE_BPS))
        a, b = Key(), Key()
        self.assertEqual(_http(f"{self.d.ipc}/api/credits/balance?pubkey={a.pub}")[0], 200)   # welcome 1000
        self.assertEqual(_http(f"{self.d.ipc}/api/credits/grant", {"to": b.pub, "amount": 500})[0], 200)
        code, r, _ = _http(f"{self.d.ipc}/api/credits/transfer", {"from": a.pub, "to": b.pub, "amount": 400})
        self.assertEqual(code, 200, r)   # only `from` gets a welcome grant here
        _, s, raw = self.d.summary()
        f = s["finance"]
        self.assertEqual(f["integrity"], "VERIFIED")
        self.assertEqual(f["entries"] - f0["entries"], 3)
        self.assertEqual(f["accounts"] - f0["accounts"], 2)
        self.assertEqual(f["welcome_grants"] - f0["welcome_grants"], 1)
        self.assertEqual(f["total_issued"] - f0["total_issued"], 1500)
        self.assertEqual(f["total_transferred"] - f0["total_transferred"], 400)
        self.assertEqual(f["fees_collected"] - f0["fees_collected"], 400 * FEE_BPS // 10000)
        self.assertNotIn(a.pub, raw)
        self.assertNotIn(b.pub, raw)


class TurnConfiguredTests(unittest.TestCase):
    def test_turn_flag_without_secret(self):
        tmp = Path(tempfile.mkdtemp(prefix="omni_telemetry_turn_"))
        d = Daemon(tmp, "turn", turn=True)
        try:
            d.start()
            code, s, raw = d.summary()
            self.assertEqual(code, 200, s)
            turn = d.proto(s, "turn")
            self.assertEqual((turn["configured"], turn["state"]), (True, "configured"))
            self.assertNotIn(TURN_SECRET, raw)
        finally:
            d.stop()
            shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipIf(_local_ip() == "127.0.0.1", "no non-loopback IP to test remote hub mode")
class RemoteHubTelemetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_telemetry_remote_"))
        cls.d = Daemon(cls.tmp, "remote", remote=True)
        cls.d.start()
        cls.token = (cls.d.home / ".omni" / "hub_token").read_text().strip()
        cls.base = f"http://{_local_ip()}:{cls.d.ports['OMNI_IPC_PORT']}"

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_bearer_gate_and_failure_count(self):
        code, _, _ = self.d.summary(base=self.base)
        self.assertEqual(code, 401)
        code, _, _ = self.d.summary(base=self.base, headers={"Authorization": "Bearer wrong-token"})
        self.assertEqual(code, 401)
        code, s, raw = self.d.summary(base=self.base, headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(code, 200, s)
        self.assertGreaterEqual(s["security"]["bearer_auth_failures"], 2)
        self.assertIsNotNone(s["security"]["last_bearer_failure_ago_s"])
        self.assertTrue(s["security"]["remote_hub"])
        self.assertIsNotNone(s["security"]["hub_token_age_s"])
        self.assertNotIn(self.token, raw)
        self.assertEqual(self.d.proto(s, "tcp_api")["listen"], ["0.0.0.0"])
        # other loopback-only paths stay closed remotely even with the token
        code, _, _ = _http(f"{self.base}/api/bugs/list", headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(code, 403)


class OffByDefaultRemoteTests(unittest.TestCase):
    @unittest.skipIf(_local_ip() == "127.0.0.1", "no non-loopback IP")
    def test_summary_not_reachable_remotely_when_hub_off(self):
        tmp = Path(tempfile.mkdtemp(prefix="omni_telemetry_off_"))
        d = Daemon(tmp, "off")
        try:
            d.start()
            base = f"http://{_local_ip()}:{d.ports['OMNI_IPC_PORT']}"
            with self.assertRaises(Exception):
                _OPENER.open(f"{base}/api/telemetry/summary", timeout=3)   # loopback bind: refused
        finally:
            d.stop()
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

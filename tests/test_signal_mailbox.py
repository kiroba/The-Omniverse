"""OmniCast signaling mailbox (daemon v8.11.0): POST /api/signal/send, GET /api/signal/poll,
GET /api/signal/ice-config.

Run: python -m unittest tests/test_signal_mailbox.py -v
Starts real daemons as subprocesses on free temp ports (OMNI_*_PORT overrides), with HOME and cwd in
temp dirs, like tests/test_bug_reports.py. OMNI_SIGNAL_TTL is shortened so expiry can be tested.
The remote-hub test talks to this machine's non-loopback IP and is skipped without one.
"""
import base64
import hashlib
import hmac
import json
import os
import shutil
import socket
import sqlite3
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daemon_version import DAEMON_VERSION  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ADMIN = ROOT / "Admin"

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_PYPATH = os.pathsep.join(p for p in [os.environ.get("PYTHONPATH", ""), str(ADMIN)] if p)
TTL_S = 3
TURN_SECRET = "test-shared-secret-not-real"
TURN_URLS = "turn:100.101.102.103:3478?transport=udp,turn:100.101.102.103:3478?transport=tcp"


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


def _http(url, data=None, headers=None, raw=None, timeout=10):
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    h = dict(headers or {})
    if body is not None:
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=h, method="POST" if body is not None else "GET")
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        txt = e.read()
        try:
            return e.code, json.loads(txt)
        except ValueError:
            return e.code, {"raw": txt[:200]}


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


_last_ts = [0]
_ts_lock = threading.Lock()


def _fresh_ts() -> int:
    """Unique ms ts per request (signatures are deterministic, reuse would be a replay)."""
    with _ts_lock:
        t = max(_now_ms(), _last_ts[0] + 1)
        _last_ts[0] = t
        return t


class Key:
    def __init__(self):
        self.sk = Ed25519PrivateKey.generate()
        self.pub = self.sk.public_key().public_bytes(serialization.Encoding.Raw,
                                                     serialization.PublicFormat.Raw).hex()

    def sign(self, data: bytes) -> str:
        return self.sk.sign(data).hex()


def send_bytes(m: dict) -> bytes:   # mirrors signal_send_bytes in the daemon (spec in the doc)
    return json.dumps({"type": "omnicast.signal.v1", "to": m["to"], "from": m["from"], "call_id": m["call_id"],
                       "kind": m["kind"], "payload": m["payload"], "ts": m["ts"]},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def auth_bytes(typ: str, field: str, pub: str, ts: int) -> bytes:
    return json.dumps({"type": typ, field: pub, "ts": ts}, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def make_msg(sender: Key, to: str, kind="offer", payload="v=0\r\no=- 1 2 IN IP4 0.0.0.0\r\n", call_id="call-1",
             ts=None) -> dict:
    m = {"to": to, "from": sender.pub, "call_id": call_id, "kind": kind, "payload": payload,
         "ts": _fresh_ts() if ts is None else ts}
    m["sig"] = sender.sign(send_bytes(m))
    return m


class Daemon:
    def __init__(self, root: Path, name: str, remote: bool = False, turn: bool = False):
        self.home, self.cwd = root / f"home_{name}", root / f"run_{name}"
        self.home.mkdir(parents=True)
        self.cwd.mkdir(parents=True)
        self.ports = {"OMNI_TELEMETRY_PORT": _free_port(), "OMNI_IPC_PORT": _free_port(),
                      "OMNI_P2P_PORT": _free_port(), "OMNI_UDP_PORT": _free_port(socket.SOCK_DGRAM)}
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home), PYTHONPATH=_PYPATH,
                        OMNI_MESH_ID=f"sig-{name}", OMNI_CATCHUP_INTERVAL="0",
                        OMNI_CATCHUP_STARTUP_DELAY="3600", NO_PROXY="*", OMNI_SIGNAL_TTL=str(TTL_S),
                        **{k: str(v) for k, v in self.ports.items()})
        for k in ("OMNI_TRUSTED_KEYS_FILE", "OMNI_LEGACY_FLOAT_TS", "OMNI_SYNC_PEERS", "OMNI_HUB_TOKEN_FILE",
                  "OMNI_HUB_REMOTE", "OMNI_HUB_BIND", "OMNI_TURN_URLS", "OMNI_TURN_SECRET", "OMNI_STUN_URLS",
                  "OMNI_TURN_TTL"):
            self.env.pop(k, None)
        if remote:
            self.env.update(OMNI_HUB_REMOTE="1", OMNI_HUB_BIND="0.0.0.0")
        if turn:
            self.env.update(OMNI_TURN_URLS=TURN_URLS, OMNI_TURN_SECRET=TURN_SECRET)
        self.ipc = f"http://127.0.0.1:{self.ports['OMNI_IPC_PORT']}"
        self.db = self.cwd / "continuity_events.db"

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
                code, body = _http(url, timeout=2)
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

    # helpers
    def send(self, msg, base=None, **kw):
        return _http(f"{base or self.ipc}/api/signal/send", msg, **kw)

    def poll(self, key: Key, since=None, wait=None, ts=None, sig=None, base=None, extra=None, **kw):
        ts = _fresh_ts() if ts is None else ts
        q = {"to": key.pub, "ts": ts,
             "sig": sig or key.sign(auth_bytes("omnicast.poll.v1", "to", key.pub, ts))}
        if since is not None:
            q["since"] = since
        if wait is not None:
            q["wait"] = wait
        q.update(extra or {})
        return _http(f"{base or self.ipc}/api/signal/poll?{urllib.parse.urlencode(q)}", **kw)

    def ice(self, key: Key, base=None, **kw):
        ts = _fresh_ts()
        q = {"pubkey": key.pub, "ts": ts, "sig": key.sign(auth_bytes("omnicast.ice-config.v1", "pubkey", key.pub, ts))}
        return _http(f"{base or self.ipc}/api/signal/ice-config?{urllib.parse.urlencode(q)}", **kw)


class SignalMailboxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_signal_"))
        cls.d = Daemon(cls.tmp, "local")
        cls.d.start()

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_version(self):
        self.assertEqual(self.d.version, DAEMON_VERSION)

    def test_send_poll_delivers_once_and_verifies_end_to_end(self):
        alice, bob = Key(), Key()
        m = make_msg(alice, bob.pub, "offer")
        code, body = self.d.send(m)
        self.assertEqual(code, 200, body)
        self.assertEqual(body["status"], "QUEUED")
        code, ice = self.d.send(make_msg(alice, bob.pub, "ice", payload=json.dumps(
            {"candidate": "candidate:1 1 udp 2122260223 100.64.0.2 50000 typ relay", "sdpMid": "0"})))
        self.assertEqual(code, 200, ice)

        code, got = self.d.poll(bob)
        self.assertEqual(code, 200, got)
        self.assertEqual(got["count"], 2)
        first = got["messages"][0]
        self.assertEqual((first["kind"], first["from"], first["payload"]), ("offer", alice.pub, m["payload"]))
        self.assertGreaterEqual(got["cursor"], first["seq"])
        # recipient can re-verify the sender's signature itself (hub can't alter the SDP)
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(first["from"])).verify(
            bytes.fromhex(first["sig"]), send_bytes(first))
        # delivered once: the next poll is empty
        code, again = self.d.poll(bob)
        self.assertEqual((code, again["count"]), (200, 0))
        # nobody else's mailbox was touched, and alice's own box is empty
        code, a = self.d.poll(alice)
        self.assertEqual((code, a["count"]), (200, 0))

    def test_non_ascii_payload_signs_as_raw_utf8(self):
        alice, bob = Key(), Key()
        m = make_msg(alice, bob.pub, kind="ring", payload='{"caller":"Kíro 🎧"}')
        self.assertIn("🎧".encode(), send_bytes(m))     # raw UTF-8 bytes, not \\u escapes (matches Dart)
        self.assertEqual(self.d.send(m)[0], 200)
        got = self.d.poll(bob)[1]["messages"]
        self.assertEqual(got[0]["payload"], m["payload"])

    def test_since_drops_already_received(self):
        alice, bob = Key(), Key()
        _, b1 = self.d.send(make_msg(alice, bob.pub, "ice", payload="{}"))
        _, b2 = self.d.send(make_msg(alice, bob.pub, "ice", payload="{}"))
        code, got = self.d.poll(bob, since=b1["seq"])
        self.assertEqual(code, 200, got)
        self.assertEqual([x["seq"] for x in got["messages"]], [b2["seq"]])

    def test_signature_rejection(self):
        alice, bob, mallory = Key(), Key(), Key()
        m = make_msg(alice, bob.pub)
        tampered = dict(m, payload=m["payload"] + "a=evil\r\n")
        self.assertEqual(self.d.send(tampered)[0], 401)
        forged = dict(m, sig=mallory.sign(send_bytes(m)))             # signed by someone else
        self.assertEqual(self.d.send(forged)[0], 401)
        redirected = dict(m, to=mallory.pub)                           # recipient swapped
        self.assertEqual(self.d.send(redirected)[0], 401)
        self.assertEqual(self.d.send(dict(m, kind="answer"))[0], 401)  # kind is signed too
        # nothing was queued
        self.assertEqual(self.d.poll(bob)[1]["count"], 0)
        self.assertEqual(self.d.poll(mallory)[1]["count"], 0)

    def test_replay_and_stale_ts(self):
        alice, bob = Key(), Key()
        m = make_msg(alice, bob.pub)
        self.assertEqual(self.d.send(m)[0], 200)
        code, body = self.d.send(m)                                   # exact replay
        self.assertEqual(code, 409, body)
        stale = make_msg(alice, bob.pub, ts=_now_ms() - 121_000)
        self.assertEqual(self.d.send(stale)[0], 401)
        future = make_msg(alice, bob.pub, ts=_now_ms() + 121_000)
        self.assertEqual(self.d.send(future)[0], 401)
        ok_old = make_msg(alice, bob.pub, ts=_now_ms() - 60_000)      # inside the window
        self.assertEqual(self.d.send(ok_old)[0], 200)
        self.assertEqual(self.d.poll(bob)[1]["count"], 2)
        # poll replay: the same signed poll can't be used twice to drain the mailbox
        self.d.send(make_msg(alice, bob.pub, kind="ring", payload=""))
        ts = _fresh_ts()
        sig = bob.sign(auth_bytes("omnicast.poll.v1", "to", bob.pub, ts))
        self.assertEqual(self.d.poll(bob, ts=ts, sig=sig)[0], 200)
        self.assertEqual(self.d.poll(bob, ts=ts, sig=sig)[0], 409)
        stale_ts = _now_ms() - 121_000
        self.assertEqual(self.d.poll(bob, ts=stale_ts,
                                     sig=bob.sign(auth_bytes("omnicast.poll.v1", "to", bob.pub, stale_ts)))[0], 401)

    def test_poll_requires_key_ownership(self):
        alice, bob, mallory = Key(), Key(), Key()
        self.assertEqual(self.d.send(make_msg(alice, bob.pub))[0], 200)
        ts = _fresh_ts()
        # mallory signs a poll for bob's mailbox with her own key
        code, _ = self.d.poll(bob, ts=ts, sig=mallory.sign(auth_bytes("omnicast.poll.v1", "to", bob.pub, ts)))
        self.assertEqual(code, 401)
        # a signature for a different purpose (ice-config) can't be reused as a poll
        ts = _fresh_ts()
        code, _ = self.d.poll(bob, ts=ts, sig=bob.sign(auth_bytes("omnicast.ice-config.v1", "pubkey", bob.pub, ts)))
        self.assertEqual(code, 401)
        q = {"to": bob.pub}                                            # unsigned
        self.assertEqual(_http(f"{self.d.ipc}/api/signal/poll?{urllib.parse.urlencode(q)}")[0], 400)
        self.assertEqual(self.d.poll(bob, extra={"evil": "1"})[0], 400)
        self.assertEqual(self.d.poll(bob, since="abc")[0], 400)
        # bob's message survived all of that
        self.assertEqual(self.d.poll(bob)[1]["count"], 1)

    def test_validation_and_size_caps(self):
        alice, bob = Key(), Key()
        m = make_msg(alice, bob.pub)
        for bad in [dict(m, kind="video"), dict(m, to="ZZ" * 32), dict(m, call_id=""), dict(m, call_id="a b"),
                    dict(m, payload=123), dict(m, ts="now"), dict(m, extra="x"),
                    {k: v for k, v in m.items() if k != "sig"}]:
            code, body = self.d.send(bad)
            self.assertEqual(code, 400, (bad.get("kind"), body))
        self.assertEqual(self.d.send(None, raw=b"{not json")[0], 400)
        self.assertEqual(self.d.send(None, raw=b"[1,2]")[0], 400)
        big = make_msg(alice, bob.pub, payload="x" * (17 * 1024))    # body over 16 KB
        self.assertEqual(self.d.send(big)[0], 413)
        over_payload = make_msg(alice, bob.pub, payload="x" * (14 * 1024 + 1))
        self.assertEqual(self.d.send(over_payload)[0], 413)
        near = make_msg(alice, bob.pub, payload="v" * (14 * 1024))   # largest allowed SDP fits
        self.assertEqual(self.d.send(near)[0], 200)
        self.assertEqual(self.d.poll(bob)[1]["count"], 1)

    def test_per_recipient_cap(self):
        bob = Key()
        senders = [Key() for _ in range(3)]   # 3 senders x 22 = 66 > 64, below each sender's burst
        codes = []
        for s in senders:
            for _ in range(22):
                codes.append(self.d.send(make_msg(s, bob.pub, "ice", payload="{}"))[0])
        self.assertEqual(codes.count(200), 64, codes)
        self.assertEqual(codes[64:], [429, 429])
        self.assertEqual(self.d.poll(bob)[1]["count"], 64)
        self.assertEqual(self.d.send(make_msg(senders[0], bob.pub, "ice", payload="{}"))[0], 200)  # room again

    def test_rate_limit_per_sender(self):
        spammer, other = Key(), Key()
        targets = [Key() for _ in range(100)]   # 100 > 40 burst + refill even on a slow box
        codes = [self.d.send(make_msg(spammer, t.pub, "ring", payload=""))[0] for t in targets]
        self.assertIn(429, codes)
        self.assertGreaterEqual(codes.count(200), 40)
        # another sender is unaffected
        self.assertEqual(self.d.send(make_msg(other, targets[0].pub, "ring", payload=""))[0], 200)

    def test_expiry(self):
        alice, bob = Key(), Key()
        self.assertEqual(self.d.send(make_msg(alice, bob.pub))[0], 200)
        time.sleep(TTL_S + 1.0)
        code, got = self.d.poll(bob)
        self.assertEqual((code, got["count"]), (200, 0))

    def test_long_poll_wakes_on_send(self):
        alice, bob = Key(), Key()
        result = {}

        def waiter():
            t0 = time.time()
            result["resp"] = self.d.poll(bob, wait=10, timeout=20)
            result["elapsed"] = time.time() - t0

        th = threading.Thread(target=waiter)
        th.start()
        time.sleep(0.8)
        self.assertEqual(self.d.send(make_msg(alice, bob.pub, "answer"))[0], 200)
        th.join(15)
        code, got = result["resp"]
        self.assertEqual((code, got["count"]), (200, 1))
        self.assertLess(result["elapsed"], 5)
        # empty long-poll returns after ~wait seconds
        t0 = time.time()
        code, got = self.d.poll(bob, wait=1)
        self.assertEqual((code, got["count"]), (200, 0))
        self.assertGreaterEqual(time.time() - t0, 0.9)

    def test_never_in_event_log(self):
        alice, bob = Key(), Key()
        marker = "OMNICAST-SECRET-SDP-MARKER"
        self.assertEqual(self.d.send(make_msg(alice, bob.pub, payload=marker))[0], 200)
        self.d.poll(bob)
        if self.d.db.exists():
            conn = sqlite3.connect(str(self.d.db))
            try:
                rows = conn.execute("SELECT action, payload_json FROM events").fetchall()
            finally:
                conn.close()
            self.assertFalse(any(marker in (r[1] or "") for r in rows))
        self.assertNotIn(marker, (self.d.cwd / "daemon.log").read_text())

    def test_ice_config_stun_only_without_turn(self):
        k = Key()
        code, cfg = self.d.ice(k)
        self.assertEqual(code, 200, cfg)
        self.assertFalse(cfg["turn"])
        self.assertEqual(cfg["ice_servers"], [{"urls": ["stun:stun.l.google.com:19302"]}])
        self.assertEqual(cfg["ice_transport_policy"], "all")
        # unsigned / wrongly signed ice-config is refused
        self.assertEqual(_http(f"{self.d.ipc}/api/signal/ice-config?pubkey={k.pub}")[0], 400)
        ts = _fresh_ts()
        q = {"pubkey": k.pub, "ts": ts, "sig": Key().sign(auth_bytes("omnicast.ice-config.v1", "pubkey", k.pub, ts))}
        self.assertEqual(_http(f"{self.d.ipc}/api/signal/ice-config?{urllib.parse.urlencode(q)}")[0], 401)


class IceConfigTurnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_signal_turn_"))
        cls.d = Daemon(cls.tmp, "turn", turn=True)
        cls.d.start()

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_turn_rest_credential_format(self):
        k = Key()
        before = int(time.time())
        code, cfg = self.d.ice(k)
        self.assertEqual(code, 200, cfg)
        self.assertTrue(cfg["turn"])
        self.assertEqual(cfg["ice_transport_policy"], "relay")
        self.assertEqual(cfg["ttl"], 3600)
        stun, turn = cfg["ice_servers"]
        self.assertEqual(stun, {"urls": ["stun:stun.l.google.com:19302"]})
        self.assertEqual(turn["urls"], TURN_URLS.split(","))
        expiry, _, who = turn["username"].partition(":")
        self.assertEqual(who, k.pub)
        self.assertTrue(before + 3600 - 5 <= int(expiry) <= int(time.time()) + 3600 + 5)
        self.assertEqual(int(expiry), cfg["expires_at"])
        want = base64.b64encode(hmac.new(TURN_SECRET.encode(), turn["username"].encode(), hashlib.sha1).digest()).decode()
        self.assertEqual(turn["credential"], want)
        # the secret itself never appears anywhere in the response
        self.assertNotIn(TURN_SECRET, json.dumps(cfg))



# --- Cross-language test vectors (OmniCast step 2, Dart client) ----------------------------------
# Fixed seeds and a message whose canonical bytes and signatures are pinned here AND in
# packages/omni_core_ui/test/omni_signal_client_test.dart on `main` (Dart). If either side changes
# how it builds the signed bytes, one of the two suites fails. Seed A = bytes 0..31 (the same key as
# the signed-event interop vectors), seed B = bytes 32..63. The payload covers CRLF, non-ASCII,
# a non-BMP emoji, quote, backslash, slash, tab, U+2028, a C0 control char and DEL.
VEC_SEED_A = bytes(range(32))
VEC_SEED_B = bytes(range(32, 64))
VEC_PUB_A = "03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8"
VEC_PUB_B = "29acbae141bccaf0b22e1a94d34d0bc7361e526d0bfe12c89794bc9322966dd7"
VEC_TS = 1793042651190
VEC_MSG = {"to": VEC_PUB_B, "from": VEC_PUB_A, "call_id": "call-vector_1.a:b", "kind": "offer",
           "payload": 'v=0\r\no=- 46117 2 IN IP4 127.0.0.1\r\ns=K\u00edro \U0001F3A7 "q" \\ /\t\u2028\u0001\u007f\r\n',
           "ts": VEC_TS}
VEC_SEND_BYTES_HEX = (
    "7b2263616c6c5f6964223a2263616c6c2d766563746f725f312e613a62222c2266726f6d223a22303361313037626666336365"
    "3130626531643730646431386537346263303939363765346436333039626135306435663164646338363634313235353331"
    "6238222c226b696e64223a226f66666572222c227061796c6f6164223a22763d305c725c6e6f3d2d203436313137203220494e"
    "20495034203132372e302e302e315c725c6e733d4bc3ad726f20f09f8ea7205c22715c22205c5c202f5c74e280a85c753030"
    "30317f5c725c6e222c22746f223a223239616362616531343162636361663062323265316139346433346430626337333631"
    "6535323664306266653132633839373934626339333232393636646437222c227473223a313739333034323635313139302c"
    "2274797065223a226f6d6e69636173742e7369676e616c2e7631227d")
VEC_SEND_SIG = ("afe1e65c40101a39de0e9f12882ff6fc42bcee1f1d2839637ad27664f5cc7d6b"
                "67fe3f3e923d7bbd5aa643a71ff0e322c733aea0435c0a96eefe96c210060209")
VEC_POLL_TEXT = '{"to":"%s","ts":1793042651191,"type":"omnicast.poll.v1"}' % VEC_PUB_B
VEC_POLL_SIG = ("ddfd60d8474e6e45f06cd64dbbcdcfda042dbe0f1604a9f9b644807c6fccc915"
                "65d1c4a68875262a536a3457ef00ea752d36999c2ba5550a2dc9192499763702")
VEC_ICE_TEXT = '{"pubkey":"%s","ts":1793042651192,"type":"omnicast.ice-config.v1"}' % VEC_PUB_A
VEC_ICE_SIG = ("8ad5e9c912765e54c0050122176af04b440e69bfde3dc50e0564ef479f32327d"
               "5dda34c195fc9ebf216e37d39663d827bf14eac1a11eada842233fcaa7c37803")


class SignalVectorTests(unittest.TestCase):
    """Pinned bytes + signatures shared with the Dart client (no daemon process needed, except the
    one test that asks the daemon module itself for its canonical bytes)."""

    @staticmethod
    def _key(seed: bytes):
        sk = Ed25519PrivateKey.from_private_bytes(seed)
        return sk, sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    def test_seeds_give_pinned_pubkeys(self):
        self.assertEqual(self._key(VEC_SEED_A)[1], VEC_PUB_A)
        self.assertEqual(self._key(VEC_SEED_B)[1], VEC_PUB_B)

    def test_send_bytes_and_signature(self):
        b = send_bytes(VEC_MSG)
        self.assertEqual(b.hex(), VEC_SEND_BYTES_HEX)
        self.assertIn("\u2028".encode("utf-8"), b)       # raw, like Dart's jsonEncode
        self.assertIn(b"\\u0001", b)                     # C0 controls escaped, lowercase hex
        self.assertEqual(self._key(VEC_SEED_A)[0].sign(b).hex(), VEC_SEND_SIG)

    def test_auth_bytes_and_signatures(self):
        pb = auth_bytes("omnicast.poll.v1", "to", VEC_PUB_B, VEC_TS + 1)
        ib = auth_bytes("omnicast.ice-config.v1", "pubkey", VEC_PUB_A, VEC_TS + 2)
        self.assertEqual(pb.decode(), VEC_POLL_TEXT)
        self.assertEqual(ib.decode(), VEC_ICE_TEXT)
        self.assertEqual(self._key(VEC_SEED_B)[0].sign(pb).hex(), VEC_POLL_SIG)
        self.assertEqual(self._key(VEC_SEED_A)[0].sign(ib).hex(), VEC_ICE_SIG)

    def test_daemon_functions_produce_the_vector(self):
        """The daemon's own signal_send_bytes / signal_auth_bytes (not just this file's mirror)."""
        tmp = Path(tempfile.mkdtemp(prefix="omni_signal_vec_"))
        try:
            code = (
                "import importlib.util, json, sys\n"
                "spec = importlib.util.spec_from_file_location('d', sys.argv[1])\n"
                "d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)\n"
                "m = json.loads(sys.argv[2])\n"
                "print(json.dumps({'send': d.signal_send_bytes(m).hex(),\n"
                "  'poll': d.signal_auth_bytes(d.SIGNAL_POLL_TYPE, m['to'], m['ts'] + 1).decode(),\n"
                "  'ice': d.signal_auth_bytes(d.SIGNAL_ICE_TYPE, m['from'], m['ts'] + 2).decode()}))\n")
            env = dict(os.environ, HOME=str(tmp), USERPROFILE=str(tmp), PYTHONPATH=_PYPATH, PYTHONUTF8="1")
            out = subprocess.run([sys.executable, "-c", code, str(ADMIN / "omni_live_daemon_server.py"),
                                  json.dumps(VEC_MSG)], cwd=tmp, env=env, capture_output=True, text=True,
                                 timeout=60)
            self.assertEqual(out.returncode, 0, out.stderr[-2000:])
            got = json.loads(out.stdout.strip().splitlines()[-1])
            self.assertEqual(got["send"], VEC_SEND_BYTES_HEX)
            self.assertEqual(got["poll"], VEC_POLL_TEXT)
            self.assertEqual(got["ice"], VEC_ICE_TEXT)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


REMOTE_IP = _local_ip()


@unittest.skipIf(REMOTE_IP.startswith("127."), "no non-loopback IP on this machine")
class RemoteHubSignalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_signal_remote_"))
        cls.d = Daemon(cls.tmp, "remote", remote=True)
        cls.d.start()
        cls.token = (cls.d.home / ".omni" / "hub_token").read_text().strip()
        cls.remote = f"http://{REMOTE_IP}:{cls.d.ports['OMNI_IPC_PORT']}"

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_remote_needs_bearer(self):
        alice, bob = Key(), Key()
        auth = {"Authorization": f"Bearer {self.token}"}
        self.assertEqual(self.d.send(make_msg(alice, bob.pub), base=self.remote)[0], 401)
        self.assertEqual(self.d.send(make_msg(alice, bob.pub), base=self.remote,
                                     headers={"Authorization": "Bearer wrong"})[0], 401)
        self.assertEqual(self.d.poll(bob, base=self.remote)[0], 401)
        self.assertEqual(self.d.ice(bob, base=self.remote)[0], 401)
        code, body = self.d.send(make_msg(alice, bob.pub), base=self.remote, headers=auth)
        self.assertEqual(code, 200, body)
        code, got = self.d.poll(bob, base=self.remote, headers=auth)
        self.assertEqual((code, got["count"]), (200, 1))
        self.assertEqual(self.d.ice(bob, base=self.remote, headers=auth)[0], 200)
        # signature rules still apply remotely
        bad = dict(make_msg(alice, bob.pub), payload="tampered")
        self.assertEqual(self.d.send(bad, base=self.remote, headers=auth)[0], 401)


class OffByDefaultRemoteTests(unittest.TestCase):
    """Without remote hub mode the signaling endpoints are loopback-only like everything else."""

    @unittest.skipIf(REMOTE_IP.startswith("127."), "no non-loopback IP on this machine")
    def test_not_reachable_remotely_when_hub_off(self):
        tmp = Path(tempfile.mkdtemp(prefix="omni_signal_off_"))
        d = Daemon(tmp, "off")
        d.start()
        try:
            base = f"http://{REMOTE_IP}:{d.ports['OMNI_IPC_PORT']}"
            try:
                code, _ = d.poll(Key(), base=base, timeout=3)
            except (urllib.error.URLError, OSError):
                code = "refused"
            self.assertIn(code, ("refused", 403))   # bound to 127.0.0.1 only: connection refused
        finally:
            d.stop()
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)

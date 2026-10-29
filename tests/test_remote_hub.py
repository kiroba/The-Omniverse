"""Opt-in remote hub (daemon v8.7.0): OMNI_HUB_REMOTE=1 + OMNI_HUB_BIND.

Run: python -m unittest tests/test_remote_hub.py -v   (no daemon needed)
Imports the daemon in-process with HOME/cwd in temp dirs. The IPC and telemetry handlers run on
ephemeral ports bound to 0.0.0.0; "remote" requests go to this machine's non-loopback IP (the
tests that need one are skipped when the machine has none).
"""
import importlib
import json
import os
import stat
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

_TMP = Path(tempfile.mkdtemp(prefix="omni_remote_hub_test_"))
os.environ["HOME"] = str(_TMP)
os.environ.pop("OMNI_TRUSTED_KEYS_FILE", None)
os.environ.pop("OMNI_LEGACY_FLOAT_TS", None)
os.environ["OMNI_MESH_ID"] = "remote-test"
os.environ["OMNI_HUB_REMOTE"] = "1"
os.environ["OMNI_HUB_BIND"] = "0.0.0.0"
os.environ.pop("OMNI_HUB_TOKEN_FILE", None)
os.environ["NO_PROXY"] = "*"
os.chdir(_TMP)

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
import omni_signing as sig  # noqa: E402
daemon = importlib.import_module("omni_live_daemon_server")  # noqa: E402
daemon.relay_event_to_peers = lambda *a, **k: None  # no network in tests

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
REMOTE_IP = daemon.get_local_ip()
HAS_REMOTE_IP = REMOTE_IP != "127.0.0.1" and not REMOTE_IP.startswith("127.")


def _http(url, data=None, headers=None):
    body = json.dumps(data).encode() if isinstance(data, dict) else data
    h = dict(headers or {})
    if body is not None:
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=h, method="POST" if body is not None else "GET")
    try:
        with _OPENER.open(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:200]}


def _phone_signed_payload(key, text="hello from phone B"):
    """What OmniHubClient.appendEvent sends after LocalEventStore signed the post with the phone key."""
    pub = sig.pubkey_hex(key)
    ts = sig.now_ms()
    inner = {"text": text}
    prev = "0x" + "0" * 64
    unsigned = {"action": "KICKBACK_POST", "author_pubkey": pub, "payload": inner,
                "previous_hash": prev, "ts": ts}
    signature = sig.sign_event(key, unsigned)
    event_id = daemon.compute_canonical_event_id("KICKBACK_POST", pub, inner, prev, None, ts)
    return pub, signature, {
        "action": "KICKBACK_POST",
        "payload": {**inner, "app_event_id": event_id, "app_author_pubkey": pub,
                    "app_signature": signature, "app_previous_hash": prev, "app_ts": ts},
        "ts": ts,
    }


class RemoteHubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        daemon.init_db()
        cls.token = daemon.STATE.hub_token
        cls.servers = [ThreadingHTTPServer(("0.0.0.0", 0), daemon.ContinuityIPCHandler),
                       ThreadingHTTPServer(("0.0.0.0", 0), daemon.TelemetryHandler)]
        for s in cls.servers:
            threading.Thread(target=s.serve_forever, daemon=True).start()
        cls.ipc = cls.servers[0].server_address[1]
        cls.tel = cls.servers[1].server_address[1]

    @classmethod
    def tearDownClass(cls):
        for s in cls.servers:
            s.shutdown()
            s.server_close()

    def setUp(self):
        daemon.HUB_REMOTE = True
        daemon.STATE.hub_token = self.token

    def remote(self, port, path):
        return f"http://{REMOTE_IP}:{port}{path}"

    def auth(self, tok=None):
        return {"Authorization": f"Bearer {tok or self.token}"}

    # --- token file ---
    def test_token_persisted_chmod_600_and_stable(self):
        p = Path(_TMP) / ".omni" / "hub_token"
        self.assertTrue(p.exists())
        self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o600)
        self.assertGreaterEqual(len(self.token), 32)
        self.assertEqual(daemon.load_or_create_hub_token(p), self.token)  # same token on restart

    def test_check_bearer(self):
        self.assertTrue(daemon.check_bearer(f"Bearer {self.token}", self.token))
        self.assertTrue(daemon.check_bearer(f"bearer {self.token}", self.token))
        self.assertFalse(daemon.check_bearer(f"Bearer {self.token}x", self.token))
        self.assertFalse(daemon.check_bearer(self.token, self.token))
        self.assertFalse(daemon.check_bearer(None, self.token))
        self.assertFalse(daemon.check_bearer(f"Bearer {self.token}", None))

    def test_listen_hosts_default_is_loopback_only(self):
        self.assertEqual(daemon.hub_listen_hosts(remote=False, bind="0.0.0.0"), ["127.0.0.1"])
        self.assertEqual(daemon.hub_listen_hosts(remote=True, bind="127.0.0.1"), ["127.0.0.1"])
        self.assertEqual(daemon.hub_listen_hosts(remote=True, bind="0.0.0.0"), ["0.0.0.0"])
        self.assertEqual(daemon.hub_listen_hosts(remote=True, bind="100.64.1.2"), ["127.0.0.1", "100.64.1.2"])

    # --- loopback unchanged ---
    def test_loopback_open_without_token(self):
        for port, path in ((self.ipc, "/api/events/feed?limit=1"), (self.ipc, "/api/events/stats"),
                           (self.tel, "/api/v1/telemetry/node-health")):
            code, _ = _http(f"http://127.0.0.1:{port}{path}")
            self.assertEqual(code, 200, path)
        code, body = _http(f"http://127.0.0.1:{self.ipc}/api/events/append",
                           {"action": "LOCAL_POST", "payload": {"text": "local"}})
        self.assertEqual(code, 200, body)
        # loopback posts are still signed by the node key, as before
        feed = _http(f"http://127.0.0.1:{self.ipc}/api/events/feed?limit=1")[1]
        self.assertEqual(feed["events"][0]["author_pubkey"], daemon.STATE.node_id)

    # --- remote needs a token ---
    @unittest.skipUnless(HAS_REMOTE_IP, "no non-loopback IP on this machine")
    def test_remote_without_token_401(self):
        for port, path in ((self.ipc, "/api/events/feed"), (self.ipc, "/api/events/stats"),
                           (self.tel, "/api/v1/telemetry/node-health")):
            code, body = _http(self.remote(port, path))
            self.assertEqual(code, 401, (path, body))
        code, _ = _http(self.remote(self.ipc, "/api/events/append"), {"action": "X", "payload": {}})
        self.assertEqual(code, 401)

    @unittest.skipUnless(HAS_REMOTE_IP, "no non-loopback IP on this machine")
    def test_remote_bad_token_401(self):
        code, _ = _http(self.remote(self.ipc, "/api/events/feed"), headers=self.auth("wrong-token"))
        self.assertEqual(code, 401)
        code, _ = _http(self.remote(self.ipc, "/api/events/feed"), headers={"Authorization": "Basic abc"})
        self.assertEqual(code, 401)

    @unittest.skipUnless(HAS_REMOTE_IP, "no non-loopback IP on this machine")
    def test_remote_good_token_200(self):
        code, body = _http(self.remote(self.ipc, "/api/events/feed?limit=5"), headers=self.auth())
        self.assertEqual(code, 200, body)
        self.assertEqual(body["version"], "8.8.0")
        code, body = _http(self.remote(self.tel, "/api/v1/telemetry/node-health"), headers=self.auth())
        self.assertEqual(code, 200, body)

    @unittest.skipUnless(HAS_REMOTE_IP, "no non-loopback IP on this machine")
    def test_remote_disallowed_path_403_even_with_token(self):
        code, _ = _http(self.remote(self.tel, "/api/omnimind/telemetry"), {"x": 1}, headers=self.auth())
        self.assertEqual(code, 403)

    @unittest.skipUnless(HAS_REMOTE_IP, "no non-loopback IP on this machine")
    def test_remote_off_is_403(self):
        daemon.HUB_REMOTE = False
        code, _ = _http(self.remote(self.ipc, "/api/events/feed"), headers=self.auth())
        self.assertEqual(code, 403)

    # --- remote posts keep the phone's signature ---
    @unittest.skipUnless(HAS_REMOTE_IP, "no non-loopback IP on this machine")
    def test_remote_post_stored_with_phone_signature(self):
        phone = Ed25519PrivateKey.generate()
        pub, signature, body = _phone_signed_payload(phone)
        code, resp = _http(self.remote(self.ipc, "/api/events/append"), body, headers=self.auth())
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp["event_id"], body["payload"]["app_event_id"])
        feed = _http(f"http://127.0.0.1:{self.ipc}/api/events/feed?limit=1")[1]
        ev = feed["events"][0]
        self.assertEqual(ev["author_pubkey"], pub)            # the phone is the author, not the node
        self.assertNotEqual(ev["author_pubkey"], daemon.STATE.node_id)
        self.assertEqual(ev["signature"], signature)          # the phone's own signature, unchanged
        self.assertTrue(ev["verified"])
        self.assertEqual(ev["payload"], {"text": "hello from phone B"})
        # same post again: dedup
        code, resp = _http(self.remote(self.ipc, "/api/events/append"), body, headers=self.auth())
        self.assertEqual((code, resp.get("result")), (200, "ALREADY_EXISTS"))

    @unittest.skipUnless(HAS_REMOTE_IP, "no non-loopback IP on this machine")
    def test_remote_post_unsigned_rejected(self):
        code, resp = _http(self.remote(self.ipc, "/api/events/append"),
                           {"action": "KICKBACK_POST", "payload": {"text": "no sig"}}, headers=self.auth())
        self.assertEqual(code, 400, resp)

    @unittest.skipUnless(HAS_REMOTE_IP, "no non-loopback IP on this machine")
    def test_remote_post_tampered_rejected(self):
        phone = Ed25519PrivateKey.generate()
        _, _, body = _phone_signed_payload(phone)
        body["payload"]["text"] = "tampered"
        body["payload"].pop("app_event_id")
        code, resp = _http(self.remote(self.ipc, "/api/events/append"), body, headers=self.auth())
        self.assertEqual(code, 401, resp)
        self.assertIn("signature", resp["message"].lower())


if __name__ == "__main__":
    unittest.main()

"""GET :5000/api/events/feed: paginated, newest-first event listing for apps (daemon v8.6.0).

Run: python -m unittest tests/test_events_feed.py -v   (no daemon needed)
Imports the daemon module in-process with HOME and cwd pointed at temp dirs, so it never touches
~/.omniverse or a real continuity_events.db. The IPC and P2P handlers run on ephemeral loopback ports.
"""
import importlib
import json
import os
import sqlite3
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

_TMP = Path(tempfile.mkdtemp(prefix="omni_feed_test_"))
os.environ["HOME"] = str(_TMP)
os.environ.pop("OMNI_TRUSTED_KEYS_FILE", None)
os.environ.pop("OMNI_LEGACY_FLOAT_TS", None)
os.environ["OMNI_MESH_ID"] = "feed-test"
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.chdir(_TMP)

import omni_signing as sig  # noqa: E402
daemon = importlib.import_module("omni_live_daemon_server")  # noqa: E402
daemon.relay_event_to_peers = lambda *a, **k: None  # no network in tests

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data else "GET")
    try:
        with _OPENER.open(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:200]}


def _fresh_dir(name):
    d = _TMP / name
    d.mkdir(exist_ok=True)
    os.chdir(d)
    daemon.STATE.seen_event_ids = set()
    return d


class FeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ipc = ThreadingHTTPServer(("127.0.0.1", 0), daemon.ContinuityIPCHandler)
        cls.p2p = ThreadingHTTPServer(("127.0.0.1", 0), daemon.P2PSyncHandler)
        for s in (cls.ipc, cls.p2p):
            threading.Thread(target=s.serve_forever, daemon=True).start()
        cls.ipc_url = f"http://127.0.0.1:{cls.ipc.server_address[1]}"
        cls.p2p_url = f"http://127.0.0.1:{cls.p2p.server_address[1]}/p2p/sync"
        cls.peer = sig.load_or_create_key(_TMP / "peer_node.key")
        cls.PEER = sig.pubkey_hex(cls.peer)
        cls.app = sig.load_or_create_key(_TMP / "peer_app.key")
        cls.APP = sig.pubkey_hex(cls.app)

    @classmethod
    def tearDownClass(cls):
        for s in (cls.ipc, cls.p2p):
            s.shutdown()
            s.server_close()
        os.chdir(_TMP)

    def setUp(self):
        _fresh_dir(self._testMethodName)
        daemon.init_db()  # genesis row (id 1)

    def feed(self, query=""):
        return _http(f"{self.ipc_url}/api/events/feed{query}")

    def append(self, action, payload):
        code, body = _http(f"{self.ipc_url}/api/events/append",
                           json.dumps({"action": action, "payload": payload}).encode(),
                           {"Content-Type": "application/json"})
        self.assertEqual(code, 200, body)
        return body["event_id"]

    def remote_post(self, text, ts=1793042651190):
        """A KICKBACK_POST as another phone's daemon relays it: node-signed, app envelope in payload."""
        app_payload = {"text": text, "app": "kickback"}
        app_ev = {"action": "KICKBACK_POST", "author_pubkey": self.APP, "payload": app_payload,
                  "previous_hash": "0x" + "0" * 64, "ts": ts}
        app_ev["signature"] = sig.sign_event(self.app, app_ev)
        app_id = daemon.compute_canonical_event_id("KICKBACK_POST", self.APP, app_payload, app_ev["previous_hash"], ts_ms=ts)
        payload = dict(app_payload, app_event_id=app_id, app_author_pubkey=self.APP,
                       app_signature=app_ev["signature"], app_previous_hash=app_ev["previous_hash"], app_ts=ts)
        ev = {"action": "KICKBACK_POST", "author_pubkey": self.PEER, "payload": payload,
              "previous_hash": "0x" + "2" * 64, "ts": ts + 5}
        ev["signature"] = sig.sign_event(self.peer, ev)
        code, body = _http(self.p2p_url, json.dumps(ev).encode(),
                           {"Content-Type": "application/json", "X-Omni-Mesh": "feed-test"})
        self.assertEqual(code, 200, body)
        return body["event_id"], app_id

    # --- tests ---------------------------------------------------------------------------------

    def test_newest_first_with_fields(self):
        a = self.append("KICKBACK_POST", {"text": "one"})
        b = self.append("KICKBACK_POST", {"text": "two"})
        code, body = self.feed()
        self.assertEqual(code, 200, body)
        self.assertEqual(body["status"], "OK")
        ids = [e["event_id"] for e in body["events"]]
        self.assertEqual(ids[:2], [b, a])
        self.assertEqual(ids[-1], "0xgenesis_000")
        top = body["events"][0]
        for k in ("id", "event_id", "type", "author_pubkey", "ts", "payload", "previous_hash", "signature", "verified", "origin"):
            self.assertIn(k, top)
        self.assertEqual(top["author_pubkey"], daemon.STATE.node_id)
        self.assertEqual(top["origin"], "local")
        self.assertTrue(top["verified"])
        self.assertEqual(top["previous_hash"], a)  # hash chain visible to the app
        self.assertFalse(body["events"][-1]["verified"])  # genesis is unsigned
        self.assertEqual(body["latest_id"], top["id"])
        self.assertFalse(body["has_more"])
        self.assertIsNone(body["next_before"])

    def test_pagination_cursor_walks_everything_once(self):
        made = [self.append("KICKBACK_POST", {"text": f"p{i}"}) for i in range(7)]
        seen, cursor, pages = [], None, 0
        while True:
            code, body = self.feed(f"?limit=3" + (f"&before={cursor}" if cursor else ""))
            self.assertEqual(code, 200, body)
            self.assertLessEqual(body["count"], 3)
            seen += [e["event_id"] for e in body["events"]]
            pages += 1
            if not body["has_more"]:
                break
            cursor = body["next_before"]
        self.assertEqual(pages, 3)  # 8 rows (7 + genesis) at 3 per page
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(seen[:7], list(reversed(made)))

    def test_since_returns_only_newer(self):
        self.append("KICKBACK_POST", {"text": "old"})
        _, body = self.feed()
        latest = body["latest_id"]
        new = self.append("KICKBACK_POST", {"text": "new"})
        _, body = self.feed(f"?since={latest}")
        self.assertEqual([e["event_id"] for e in body["events"]], [new])

    def test_limit_capped_at_200_and_default_50(self):
        conn = sqlite3.connect("continuity_events.db")
        conn.executemany("INSERT INTO events (event_id, action, author_pubkey, previous_hash, timestamp, payload_json) "
                         "VALUES (?, 'BULK', 'x', '0x', 1700000000.0, '{}')", [(f"0xbulk{i}",) for i in range(260)])
        conn.commit()
        conn.close()
        _, body = self.feed("?limit=10000")
        self.assertEqual(body["limit"], 200)
        self.assertEqual(body["count"], 200)
        self.assertTrue(body["has_more"])
        _, body = self.feed()
        self.assertEqual(body["count"], 50)
        _, body = self.feed("?limit=0")
        self.assertEqual(body["count"], 1)

    def test_type_filter(self):
        self.append("OTHER_ACTION", {"x": 1})
        p = self.append("KICKBACK_POST", {"text": "hi"})
        _, body = self.feed("?type=KICKBACK_POST")
        self.assertEqual([e["event_id"] for e in body["events"]], [p])

    def test_bad_params_400(self):
        for q in ("?limit=abc", "?before=-1", "?type=bad%20type", "?foo=1"):
            code, body = self.feed(q)
            self.assertEqual(code, 400, (q, body))
            self.assertEqual(body["status"], "ERROR")

    def test_empty_db(self):
        _fresh_dir("empty_no_db")  # no continuity_events.db at all
        code, body = self.feed()
        self.assertEqual(code, 200, body)
        self.assertEqual((body["events"], body["count"], body["latest_id"], body["has_more"]), ([], 0, 0, False))
        conn = sqlite3.connect("continuity_events.db")  # table exists but has no rows
        conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL, "
                     "action TEXT NOT NULL, author_pubkey TEXT NOT NULL, previous_hash TEXT NOT NULL, timestamp REAL NOT NULL, "
                     "payload_json TEXT DEFAULT '{}', signature TEXT, ts_ms INTEGER)")
        conn.commit()
        conn.close()
        code, body = self.feed()
        self.assertEqual(code, 200, body)
        self.assertEqual(body["events"], [])

    def test_remote_event_from_p2p_sync_is_listed(self):
        local = self.append("KICKBACK_POST", {"text": "mine"})
        remote_id, app_id = self.remote_post("from the other phone")
        _, body = self.feed("?type=KICKBACK_POST")
        by_id = {e["event_id"]: e for e in body["events"]}
        self.assertIn(local, by_id)
        r = by_id[remote_id]
        self.assertEqual(r["origin"], "remote")
        self.assertEqual(r["author_pubkey"], self.PEER)
        self.assertTrue(r["verified"])
        self.assertEqual(r["payload"]["text"], "from the other phone")
        self.assertEqual(r["payload"]["app_event_id"], app_id)
        self.assertEqual(r["payload"]["app_author_pubkey"], self.APP)
        # The app envelope inside the payload re-verifies against the app key.
        app_payload = {k: v for k, v in r["payload"].items() if not k.startswith("app_")}
        self.assertTrue(sig.verify_event({"action": "KICKBACK_POST", "author_pubkey": r["payload"]["app_author_pubkey"],
                                          "payload": app_payload, "previous_hash": r["payload"]["app_previous_hash"],
                                          "ts": r["payload"]["app_ts"], "signature": r["payload"]["app_signature"]}))

    def test_tampered_row_reads_unverified(self):
        eid = self.append("KICKBACK_POST", {"text": "original"})
        conn = sqlite3.connect("continuity_events.db")
        conn.execute("UPDATE events SET payload_json = ? WHERE event_id = ?", (json.dumps({"text": "edited"}), eid))
        conn.commit()
        conn.close()
        _, body = self.feed()
        self.assertFalse(next(e for e in body["events"] if e["event_id"] == eid)["verified"])

    def test_legacy_float_timestamp_event(self):
        conn = sqlite3.connect("continuity_events.db")
        conn.execute("INSERT INTO events (event_id, action, author_pubkey, previous_hash, timestamp, payload_json) "
                     "VALUES ('0xlegacy', 'KICKBACK_POST', 'ab', '0x', 1793042651.19, '{}')")
        conn.commit()
        conn.close()
        _, body = self.feed("?limit=1")
        e = body["events"][0]
        self.assertEqual(e["timestamp"], 1793042651.19)
        self.assertNotIn("ts", e)
        self.assertEqual(e["ts_ms"], 1793042651190)

    def test_non_loopback_client_refused(self):
        self.assertTrue(daemon._is_loopback("127.0.0.1"))
        self.assertTrue(daemon._is_loopback("::1"))
        self.assertFalse(daemon._is_loopback("192.168.1.20"))

    def test_old_routes_unchanged(self):
        code, body = _http(f"{self.ipc_url}/api/events/list")
        self.assertEqual(code, 200)
        self.assertIn("total_events", body)


if __name__ == "__main__":
    unittest.main()

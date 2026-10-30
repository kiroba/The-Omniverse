"""Daemon v8.12.1: chunked request bodies (the KickBack "posts never show up" bug).

KickBack's OmniHubClient._post used req.write(...) without contentLength, so dart:io sent
"Transfer-Encoding: chunked" and no Content-Length. The daemon read Content-Length (missing -> 0), parsed
"{}" and stored an EMPTY "USER_ACTION" event with status SUCCESS. The app marked the post synced and
its feed (?type=KICKBACK_POST) never matched. These tests send bodies exactly that way.

Run: python3 -m unittest tests.test_request_bodies
"""
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daemon_harness import Daemon, Key, daemon_module, now_ms, post_chunked, post_raw  # noqa: E402
from daemon_version import DAEMON_VERSION  # noqa: E402

d = daemon_module()


def kickback_post_body(key: Key, text: str) -> dict:
    """What LocalEventStore.syncToHubDetailed sends: action, payload + app_* envelope, int-ms ts."""
    ts = now_ms()
    app_ev = key.sign_event({"action": "KICKBACK_POST", "author_pubkey": key.pub,
                             "payload": {"text": text, "app": "kickback"},
                             "previous_hash": "0x" + "0" * 64, "ts": ts})
    payload = {"text": text, "app": "kickback", "app_event_id": app_ev["event_id"],
               "app_author_pubkey": key.pub, "app_signature": app_ev["signature"],
               "app_previous_hash": app_ev["previous_hash"], "app_ts": ts}
    return {"action": "KICKBACK_POST", "payload": payload, "ts": ts}


class FakeHandler:
    def __init__(self, headers: dict, body: bytes):
        self.headers, self.rfile = headers, io.BytesIO(body)


class ReadBodyUnit(unittest.TestCase):
    def test_content_length(self):
        self.assertEqual(d.read_request_body(FakeHandler({"Content-Length": "5"}, b"hello"), 100), b"hello")

    def test_no_body(self):
        self.assertEqual(d.read_request_body(FakeHandler({}, b""), 100), b"")

    def test_chunked_with_extension_and_trailer(self):
        raw = b"4;ext=1\r\nWiki\r\n5\r\npedia\r\n0\r\nX-Trailer: 1\r\n\r\n"
        h = FakeHandler({"Transfer-Encoding": "chunked"}, raw)
        self.assertEqual(d.read_request_body(h, 100), b"Wikipedia")

    def test_chunked_too_large(self):
        raw = b"a\r\n0123456789\r\n0\r\n\r\n"
        with self.assertRaises(d.BodyError) as cm:
            d.read_request_body(FakeHandler({"Transfer-Encoding": "chunked"}, raw), 5)
        self.assertEqual(cm.exception.status, 413)

    def test_chunked_malformed(self):
        for raw in (b"zz\r\nabc\r\n0\r\n\r\n", b"5\r\nab", b"3\r\nabcX\r\n0\r\n\r\n"):
            with self.assertRaises(d.BodyError) as cm:
                d.read_request_body(FakeHandler({"Transfer-Encoding": "chunked"}, raw), 100)
            self.assertEqual(cm.exception.status, 400, raw)

    def test_bad_content_length(self):
        for v in ("abc", "-1"):
            with self.assertRaises(d.BodyError):
                d.read_request_body(FakeHandler({"Content-Length": v}, b""), 100)
        with self.assertRaises(d.BodyError) as cm:
            d.read_request_body(FakeHandler({"Content-Length": "500"}, b"x"), 100)
        self.assertEqual(cm.exception.status, 413)


class LiveDaemonBodies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_bodies_"))
        cls.d = Daemon(cls.tmp, "bodies").start()
        cls.key = Key()

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_version(self):
        self.assertEqual(self.d.version, DAEMON_VERSION)

    def test_chunked_kickback_post_lands_in_feed(self):
        body = kickback_post_body(self.key, "chunked hello")
        code, resp = post_chunked(self.d.ipc_port, "/api/events/append", body)
        self.assertEqual((code, resp["status"]), (200, "SUCCESS"), resp)
        code, feed = self.d.get("/api/events/feed", {"type": "KICKBACK_POST", "limit": 50})
        self.assertEqual(code, 200)
        mine = [e for e in feed["events"] if e["event_id"] == resp["event_id"]]
        self.assertEqual(len(mine), 1, feed)
        ev = mine[0]
        self.assertEqual(ev["payload"]["text"], "chunked hello")
        self.assertEqual(ev["payload"]["app_author_pubkey"], self.key.pub)
        self.assertEqual(ev["ts"], body["ts"])
        self.assertTrue(ev["verified"])

    def test_chunked_body_split_across_chunks(self):
        import json
        raw = json.dumps(kickback_post_body(self.key, "split")).encode()
        code, resp = post_chunked(self.d.ipc_port, "/api/events/append", raw_chunks=[raw[:7], raw[7:30], raw[30:]])
        self.assertEqual(code, 200, resp)

    def test_content_length_post_still_works(self):
        code, resp = self.d.post("/api/events/append", kickback_post_body(self.key, "with length"))
        self.assertEqual((code, resp["status"]), (200, "SUCCESS"), resp)

    def test_empty_append_rejected_not_stored(self):
        before = self.d.event_count()
        port = self.d.ipc_port
        for req in (b"POST /api/events/append HTTP/1.1\r\nHost: x\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",
                    b"POST /api/events/append HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n",
                    b"POST /api/events/append HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n"
                    b"Connection: close\r\n\r\n0\r\n\r\n"):
            self.assertEqual(post_raw(port, req), 400, req)
        code, resp = self.d.post("/api/events/append", {})
        self.assertEqual(code, 400, resp)
        code, resp = self.d.post("/api/events/append", [1, 2])
        self.assertEqual(code, 400, resp)
        self.assertEqual(self.d.event_count(), before)

    def test_malformed_chunked_400(self):
        req = (b"POST /api/events/append HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n"
               b"Connection: close\r\n\r\nzz\r\n{}\r\n0\r\n\r\n")
        self.assertEqual(post_raw(self.d.ipc_port, req), 400)

    def test_chunked_bug_report_and_signal(self):
        code, resp = post_chunked(self.d.ipc_port, "/api/bugs/report",
                                  {"what_happened": "chunked report", "app": "KickBack"})
        self.assertEqual(code, 200, resp)
        # Signal send: body is parsed (validation error), not refused for a missing Content-Length.
        code, resp = post_chunked(self.d.ipc_port, "/api/signal/send", {"to": "nope"})
        self.assertEqual(code, 400, resp)
        self.assertNotIn("Content-Length", resp.get("message", ""))

    def test_chunked_oversize_signal_413(self):
        # Declares a 20 KB chunk (cap 16 KB) and sends only its start: the daemon answers 413 from the
        # size line, before reading the data (a full upload races the server's close -> reset).
        req = (b"POST /api/signal/send HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n"
               b"Connection: close\r\n\r\n5000\r\n" + b"x" * 64)
        self.assertEqual(post_raw(self.d.ipc_port, req), 413)


if __name__ == "__main__":
    unittest.main()

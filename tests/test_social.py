"""Daemon v8.14.0: KickBack comments + reactions (person-signed, keyed to a post id).

Run: python3 -m unittest tests.test_social
"""
import shutil
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daemon_harness import Daemon, Key, daemon_module, now_ms  # noqa: E402
from test_request_bodies import kickback_post_body  # noqa: E402

ZERO = "0x" + "0" * 64


def signed(key: Key, action: str, payload: dict, ts=None, prev=ZERO) -> dict:
    return key.sign_event({"action": action, "author_pubkey": key.pub, "payload": payload,
                           "previous_hash": prev, "ts": ts if ts is not None else now_ms()})


def comment(key, post_id, text, ts=None, **extra):
    return signed(key, "kickback_comment", {"schema": 1, "post_id": post_id, "text": text, **extra}, ts)


def react(key, post_id, reaction, on=True, ts=None):
    return signed(key, "kickback_reaction", {"schema": 1, "post_id": post_id, "reaction": reaction, "on": on}, ts)


class Unit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = daemon_module()

    def test_validators(self):
        pid = "0x" + "a" * 64
        self.d.validate_comment({"schema": 1, "post_id": pid, "text": "hi\nthere"})
        self.d.validate_reaction({"schema": 1, "post_id": pid, "reaction": "🔥", "on": True})
        for bad in ({"schema": 1, "post_id": pid, "text": ""}, {"schema": 1, "post_id": "0x12", "text": "x"},
                    {"schema": 1, "post_id": pid, "text": "x" * 2001}, {"schema": 1, "post_id": pid, "text": "x", "y": 1},
                    {"schema": 1, "post_id": pid, "text": "x", "reply_to": "nope"}):
            with self.assertRaises(ValueError, msg=bad):
                self.d.validate_comment(bad)
        for bad in ({"schema": 1, "post_id": pid, "reaction": "two words", "on": True},
                    {"schema": 1, "post_id": pid, "reaction": "x" * 17, "on": True},
                    {"schema": 1, "post_id": pid, "reaction": "ok", "on": 1},
                    {"schema": 1, "post_id": pid, "reaction": "ok"}):
            with self.assertRaises(ValueError, msg=bad):
                self.d.validate_reaction(bad)


class LiveSocial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_social_"))
        cls.d = Daemon(cls.tmp, "social", env={"OMNI_USER_RATE_MAX": "50"}).start()
        cls.author = Key()
        body = kickback_post_body(cls.author, "a post to talk about")
        code, r = cls.d.post("/api/events/append", body)
        assert code == 200, r
        cls.post_id = body["payload"]["app_event_id"]   # what KickBack shows (HubFeedEvent.dedupeKey)

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_thread_comments_reactions(self):
        a, b = Key(), Key()
        self.d.post("/api/profile/update", signed(a, "profile_update", {"schema": 1, "handle": "alice"}))
        c1 = comment(a, self.post_id, "first!", ts=now_ms() - 2000)
        code, r = self.d.post("/api/social/comment", c1)
        self.assertEqual(code, 200, r)
        c2 = comment(b, self.post_id, "reply", reply_to=c1["event_id"])
        self.assertEqual(self.d.post("/api/social/comment", c2)[0], 200)
        for k, rx in ((a, "🔥"), (b, "🔥"), (b, "lol")):
            self.assertEqual(self.d.post("/api/social/react", react(k, self.post_id, rx))[0], 200)
        code, t = self.d.get("/api/social/thread", {"post_id": self.post_id, "viewer": b.pub})
        self.assertEqual(code, 200, t)
        self.assertTrue(t["post_known"])
        self.assertEqual(t["post"]["author_pubkey"], self.author.pub)
        self.assertEqual([c["text"] for c in t["comments"]], ["first!", "reply"])
        self.assertEqual(t["comments"][0]["handle_display"], f"@alice.{a.pub[:4]}")
        self.assertIsNone(t["comments"][1]["handle_display"])
        self.assertEqual(t["comments"][1]["reply_to"], c1["event_id"])
        self.assertEqual(t["reactions"], {"🔥": 2, "lol": 1})
        self.assertEqual(t["my_reactions"], ["lol", "🔥"])

    def test_reaction_toggle_latest_ts_wins(self):
        k = Key()
        pid = "0x" + "b" * 64   # a post this hub hasn't seen (yet)
        t0 = now_ms()
        self.assertEqual(self.d.post("/api/social/react", react(k, pid, "👍", True, ts=t0))[0], 200)
        self.assertEqual(self.d.post("/api/social/react", react(k, pid, "👍", False, ts=t0 + 10))[0], 200)
        # A late, older "on" doesn't resurrect it.
        self.assertEqual(self.d.post("/api/social/react", react(k, pid, "👍", True, ts=t0 - 10))[0], 200)
        code, t = self.d.get("/api/social/thread", {"post_id": pid})
        self.assertEqual((code, t["reactions"], t["post_known"]), (200, {}, False))
        # Same person reacting twice "on" counts once.
        self.d.post("/api/social/react", react(k, pid, "👀", True, ts=t0 + 20))
        self.d.post("/api/social/react", react(k, pid, "👀", True, ts=t0 + 30))
        self.assertEqual(self.d.get("/api/social/thread", {"post_id": pid})[1]["reactions"], {"👀": 1})

    def test_counts_batch(self):
        pid2 = "0x" + "c" * 64
        k = Key()
        self.d.post("/api/social/comment", comment(k, pid2, "on another post"))
        self.d.post("/api/social/react", react(k, pid2, "❤"))
        code, r = self.d.get("/api/social/counts", {"post_ids": f"{self.post_id},{pid2}", "viewer": k.pub})
        self.assertEqual(code, 200, r)
        self.assertEqual(r["posts"][pid2], {"comments": 1, "reactions": {"❤": 1}, "my_reactions": ["❤"]})
        self.assertIn(self.post_id, r["posts"])
        self.assertEqual(self.d.get("/api/social/counts", {"post_ids": ",".join(["0x" + "d" * 64] * 101)})[0], 400)
        self.assertEqual(self.d.get("/api/social/counts", {})[0], 400)

    def test_rejections(self):
        k = Key()
        c = comment(k, self.post_id, "legit")
        self.assertEqual(self.d.post("/api/social/comment", dict(c, payload=dict(c["payload"], text="edited")))[0], 401)
        self.assertEqual(self.d.post("/api/social/comment", react(k, self.post_id, "x"))[0], 400)   # wrong action
        self.assertEqual(self.d.post("/api/social/react", comment(k, self.post_id, "x"))[0], 400)
        code, r = self.d.post("/api/events/append", {"action": "kickback_comment", "payload": {"text": "x"}})
        self.assertEqual(code, 403, r)
        code, r = self.d.post("/api/events/append", {"action": "kickback_reaction", "payload": {}})
        self.assertEqual(code, 403, r)
        self.assertEqual(self.d.get("/api/social/thread", {"post_id": "nope"})[0], 400)

    def test_peer_relayed_garbage_is_ignored(self):
        """A validly SIGNED reaction with a bad schema that arrives over /p2p/sync is stored (peers only
        check signatures) but never counted."""
        import json
        import urllib.request
        k = Key()
        pid = "0x" + "e" * 64
        bad = signed(k, "kickback_reaction", {"schema": 1, "post_id": pid, "reaction": "two words", "on": True})
        req = urllib.request.Request(f"http://127.0.0.1:{self.d.ports['OMNI_P2P_PORT']}/p2p/sync",
                                     data=json.dumps(bad).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Omni-Mesh": "t-social"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=5) as r:
                self.assertEqual(r.status, 200)
        except urllib.error.HTTPError as e:   # noqa: F821 - only if the gate refuses; then nothing stored
            self.skipTest(f"p2p gate refused the test event: {e.code}")
        code, t = self.d.get("/api/social/thread", {"post_id": pid})
        self.assertEqual((code, t["reactions"]), (200, {}))


if __name__ == "__main__":
    unittest.main()

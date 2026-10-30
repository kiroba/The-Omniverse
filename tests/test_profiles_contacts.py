"""Daemon v8.13.0: person-signed profiles, contact cards (QR), hub card, invite codes.

Run: python3 -m unittest tests.test_profiles_contacts
"""
import base64
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daemon_harness import Daemon, Key, daemon_module, http, now_ms  # noqa: E402

ZERO = "0x" + "0" * 64


def profile_event(key: Key, handle="keith_b", ts=None, prev=ZERO, **extra) -> dict:
    payload = {"schema": 1, "handle": handle, **extra}
    return key.sign_event({"action": "profile_update", "author_pubkey": key.pub, "payload": payload,
                           "previous_hash": prev, "ts": ts if ts is not None else now_ms()})


def card_bytes(card: dict) -> bytes:
    return json.dumps({k: v for k, v in card.items() if k != "sig"}, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def contact_card(key: Key, handle="keith_b", ts=None, **extra) -> dict:
    card = {"type": "omni.contact-card.v1", "pubkey": key.pub, "handle": handle,
            "ts": ts if ts is not None else now_ms(), **extra}
    card["sig"] = key.sign(card_bytes(card))
    return card


class UnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = daemon_module()

    def test_handle_display(self):
        self.assertEqual(self.d.handle_display("keith", "ab12" + "0" * 60), "@keith.ab12")

    def test_validate_profile(self):
        ok = {"schema": 1, "handle": "abc", "display_name": "Keith", "bio": "line1\nline2", "omnicast": True}
        self.assertEqual(self.d.validate_profile(ok), ok)
        for bad in ({"handle": "abc"}, {"schema": 1, "handle": "AB"}, {"schema": 1, "handle": "abc", "x": 1},
                    {"schema": 1, "handle": "abc", "display_name": " pad "}, {"schema": 1, "handle": "abc", "omnicast": "y"},
                    {"schema": 1, "handle": "abc", "bio": "x" * 281}):
            with self.assertRaises(ValueError, msg=bad):
                self.d.validate_profile(bad)

    def test_card_signature_and_qr_roundtrip(self):
        k = Key()
        card = contact_card(k, display_name="Kéith ✓")
        self.assertEqual(self.d.verify_contact_card(card), card)
        qr = "omni://contact?c=" + self.d._b64url_json(card)
        self.assertEqual(self.d.decode_qr_payload(qr, "contact"), card)
        forged = dict(card, handle="someone")
        with self.assertRaises(ValueError):
            self.d.verify_contact_card(forged)
        other = Key()
        with self.assertRaises(ValueError):
            self.d.verify_contact_card(dict(card, pubkey=other.pub))

    def test_rate_limiter(self):
        t = [0.0]
        lim = self.d.SlidingWindowLimiter(3, 60.0, clock=lambda: t[0])
        self.assertEqual([lim.allow("a") for _ in range(4)], [True, True, True, False])
        self.assertTrue(lim.allow("b"))
        t[0] = 61.0
        self.assertTrue(lim.allow("a"))


class LiveProfiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_profiles_"))
        cls.d = Daemon(cls.tmp, "profiles", env={"OMNI_USER_RATE_MAX": "8"}).start()

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_profile_update_and_read(self):
        k = Key()
        ev1 = profile_event(k, "first_name", ts=now_ms() - 5000, display_name="First")
        code, r = self.d.post("/api/profile/update", ev1)
        self.assertEqual((code, r["status"]), (200, "SUCCESS"), r)
        self.assertEqual(r["event_id"], ev1["event_id"])
        ev2 = profile_event(k, "second_name", prev=ev1["event_id"], display_name="Second", omnicast=True)
        self.assertEqual(self.d.post("/api/profile/update", ev2)[0], 200)
        # An older event arriving late does not win.
        old = profile_event(k, "stale", ts=now_ms() - 60_000)
        self.assertEqual(self.d.post("/api/profile/update", old)[0], 200)
        code, r = self.d.get("/api/profile", {"pubkey": k.pub})
        self.assertEqual(code, 200, r)
        p = r["profile"]
        self.assertEqual((p["handle"], p["display_name"], p["omnicast"]), ("second_name", "Second", True))
        self.assertEqual(p["handle_display"], f"@second_name.{k.pub[:4]}")
        # Stored with the person as author, exactly as signed.
        code, feed = self.d.get("/api/events/feed", {"type": "profile_update", "limit": 50})
        mine = [e for e in feed["events"] if e["event_id"] == ev2["event_id"]]
        self.assertEqual(mine[0]["author_pubkey"], k.pub)
        self.assertTrue(mine[0]["verified"])
        # Replay = ALREADY_EXISTS, not a second row.
        self.assertEqual(self.d.post("/api/profile/update", ev2)[1].get("result"), "ALREADY_EXISTS")

    def test_profile_rejections(self):
        k = Key()
        ev = profile_event(k)
        forged = dict(ev, payload=dict(ev["payload"], handle="hijack"))
        self.assertEqual(self.d.post("/api/profile/update", forged)[0], 401)
        other = Key()
        self.assertEqual(self.d.post("/api/profile/update", dict(ev, author_pubkey=other.pub))[0], 401)
        bad = profile_event(k, "NO")
        self.assertEqual(self.d.post("/api/profile/update", bad)[0], 400)
        self.assertEqual(self.d.post("/api/profile/update", dict(ev, extra=1))[0], 400)
        self.assertEqual(self.d.post("/api/profile/update", dict(ev, event_id="0x" + "1" * 64))[0], 400)
        # Generic append can't write profile events (no schema check there).
        code, r = self.d.post("/api/events/append", {"action": "profile_update", "payload": {"handle": "x"}})
        self.assertEqual(code, 403, r)
        self.assertEqual(self.d.get("/api/profile", {"pubkey": Key().pub})[0], 404)
        self.assertEqual(self.d.get("/api/profile", {"pubkey": "zz"})[0], 400)

    def test_rate_limit_per_key(self):
        k = Key()
        codes = [self.d.post("/api/profile/update", profile_event(k, f"user_{i:03d}", ts=now_ms() + i))[0]
                 for i in range(10)]
        self.assertEqual(codes[:8], [200] * 8)
        self.assertEqual(codes[8:], [429, 429])
        self.assertEqual(self.d.post("/api/profile/update", profile_event(Key(), "fresh_key"))[0], 200)

    def test_list_and_search(self):
        a, b = Key(), Key()
        self.d.post("/api/profile/update", profile_event(a, "zed_alpha", display_name="Zed"))
        self.d.post("/api/profile/update", profile_event(b, "zed_beta"))
        code, r = self.d.get("/api/profile/list", {"q": "@zed_", "limit": 10})
        self.assertEqual(code, 200, r)
        self.assertEqual({p["pubkey"] for p in r["profiles"]}, {a.pub, b.pub})
        code, r = self.d.get("/api/profile/list", {"q": "zed_", "limit": 1})
        self.assertEqual((r["count"], r["has_more"]), (1, True))
        self.assertEqual(self.d.get("/api/profile/list", {"bogus": 1})[0], 400)


class LiveContactsInvites(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_contacts_"))
        cls.d = Daemon(cls.tmp, "contacts").start()

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_verify_card_and_qr(self):
        k = Key()
        card = contact_card(k, display_name="Keith", hub={"host": "100.101.102.103", "ipc_port": 5000})
        code, r = self.d.post("/api/contacts/verify", card)
        self.assertEqual((code, r["valid"]), (200, True), r)
        self.assertEqual(r["handle_display"], f"@keith_b.{k.pub[:4]}")
        code, r2 = self.d.post("/api/contacts/verify", {"qr": r["qr"]})
        self.assertEqual((code, r2["card"]), (200, card))
        self.assertEqual(self.d.post("/api/contacts/verify", dict(card, handle="evil"))[0], 400)
        self.assertEqual(self.d.post("/api/contacts/verify", {"qr": "omni://contact?c=!!"})[0], 400)
        self.assertEqual(self.d.post("/api/contacts/verify", contact_card(k, ts=now_ms() + 3_600_000))[0], 400)

    def test_hub_card_is_node_signed_and_has_no_token(self):
        d = daemon_module()
        code, r = self.d.get("/api/hub/card")
        self.assertEqual(code, 200, r)
        card = r["card"]
        self.assertEqual((card["type"], card["node_id"]), ("omni.hub-card.v1", self.d.node_id))
        self.assertTrue(d._ed25519_ok(card["node_id"], card["sig"], card_bytes(card)))
        self.assertNotIn("token", json.dumps(card).lower())
        b = r["qr"].split("c=", 1)[1]
        self.assertEqual(json.loads(base64.urlsafe_b64decode(b + "=" * (-len(b) % 4))), card)

    def test_invite_create_redeem_use_up(self):
        k = Key()
        card = contact_card(k)
        code, r = self.d.post("/api/invites/create", {"card": card, "max_uses": 2, "ttl_s": 600})
        self.assertEqual(code, 200, r)
        inv = r["code"]
        self.assertRegex(inv, r"^[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}$")
        code, got = self.d.get("/api/invites/redeem", {"code": inv.lower().replace("-", "")})
        self.assertEqual((code, got["card"], got["uses_left"]), (200, card, 1), got)
        self.assertEqual(self.d.get("/api/invites/redeem", {"code": inv})[0], 200)
        self.assertEqual(self.d.get("/api/invites/redeem", {"code": inv})[0], 404)   # used up
        self.assertEqual(self.d.get("/api/invites/redeem", {"code": "2222-2222"})[0], 404)
        self.assertEqual(self.d.get("/api/invites/redeem", {"code": "bad"})[0], 400)

    def test_invite_rejections(self):
        k = Key()
        stale = contact_card(k, ts=now_ms() - 3_600_000)
        self.assertEqual(self.d.post("/api/invites/create", {"card": stale})[0], 400)
        self.assertEqual(self.d.post("/api/invites/create", {"card": contact_card(k), "ttl_s": 10**9})[0], 400)
        self.assertEqual(self.d.post("/api/invites/create", {"card": dict(contact_card(k), handle="x_y_z")})[0], 400)

    def test_invite_survives_restart(self):
        k = Key()
        code, r = self.d.post("/api/invites/create", {"card": contact_card(k)})
        self.assertEqual(code, 200, r)
        self.d.restart()
        self.assertEqual(self.d.get("/api/invites/redeem", {"code": r["code"]})[0], 200)

    def test_redeem_bruteforce_throttled(self):
        codes = [self.d.get("/api/invites/redeem", {"code": f"{i:04d}".replace("0", "2").replace("1", "3") + "-ZZZZ"})[0]
                 for i in range(22)]
        self.assertIn(429, codes)


def _local_ip() -> str:
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


REMOTE_IP = _local_ip()


@unittest.skipIf(REMOTE_IP.startswith("127."), "no non-loopback IP on this machine")
class RemoteHubAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_profiles_remote_"))
        cls.d = Daemon(cls.tmp, "premote", remote=True).start()
        cls.token = (cls.d.home / ".omni" / "hub_token").read_text().strip()
        cls.base = f"http://{REMOTE_IP}:{cls.d.ipc_port}"

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_remote_profile_and_card_with_token(self):
        k = Key()
        auth = {"Authorization": f"Bearer {self.token}"}
        self.assertEqual(http(f"{self.base}/api/profile/update", profile_event(k, "remote_user"))[0], 401)
        code, r = http(f"{self.base}/api/profile/update", profile_event(k, "remote_user"), headers=auth)
        self.assertEqual(code, 200, r)
        code, r = http(f"{self.base}/api/profile?pubkey={k.pub}", headers=auth)
        self.assertEqual((code, r["profile"]["handle"]), (200, "remote_user"))
        code, r = http(f"{self.base}/api/hub/card", headers=auth)
        self.assertEqual(code, 200, r)
        self.assertTrue(r["card"]["remote_hub"])
        self.assertNotIn(self.token, json.dumps(r))


if __name__ == "__main__":
    unittest.main()

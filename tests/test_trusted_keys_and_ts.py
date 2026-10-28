"""Trusted-key allowlist (403) + integer-ms "ts" canonical form.

Run: python -m unittest tests/test_trusted_keys_and_ts.py -v   (no daemon needed)
Imports the daemon module in-process with HOME and cwd pointed at a temp dir, so it never
touches ~/.omniverse or a real continuity_events.db.
"""
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ADMIN = Path(__file__).resolve().parent.parent / "Admin"
sys.path.insert(0, str(ADMIN))

_TMP = Path(tempfile.mkdtemp(prefix="omni_trust_test_"))
os.environ["HOME"] = str(_TMP)
os.environ.pop("OMNI_TRUSTED_KEYS_FILE", None)
os.environ.pop("OMNI_LEGACY_FLOAT_TS", None)
os.chdir(_TMP)

import omni_signing as sig  # noqa: E402
daemon = importlib.import_module("omni_live_daemon_server")  # noqa: E402
daemon.init_db()

PEER = "10.0.0.9"
alice = sig.load_or_create_key(_TMP / "alice.key")
mallory = sig.load_or_create_key(_TMP / "mallory.key")
ALICE, MALLORY = sig.pubkey_hex(alice), sig.pubkey_hex(mallory)

# Vector from packages/omni_core_ui/test/interop_test.dart (main @ 4b4819b, PR #18).
DART_PUB = "03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8"
DART_EVENT = {
    "action": "CREATOR_POST_PUBLISHED", "author_pubkey": DART_PUB,
    "payload": {"title": "Sovereign Post", "tier": "PUBLIC", "emoji": "h\u00e9llo \U0001F600",
                "n": 3, "nested": {"b": 1.5, "a": [True, None]}},
    "previous_hash": "0xgenesis_000", "timestamp": 1793042651.19,
}
DART_CANONICAL = r'{"action":"CREATOR_POST_PUBLISHED","author_pubkey":"03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8","payload":{"emoji":"h\u00e9llo \ud83d\ude00","n":3,"nested":{"a":[true,null],"b":1.5},"tier":"PUBLIC","title":"Sovereign Post"},"previous_hash":"0xgenesis_000","timestamp":1793042651.19}'
DART_ID = "0xfa3a7ba832dae9cb8dd24af8a922f6c159862eddd6b7cef3765eafd58fb07458"
DART_SIG = "d9755fc457c659d01ecab8e14f3fca2f671be756cc4ebd35e05c805acd52e0bbc3b5d8f7085be00a10b8dddfeb7765d55b0e4782eb9ca10742c731d6867d9008"

_n = 0


def signed(key, pub, use_ms=True):
    global _n
    _n += 1
    ev = {"action": "CHAT", "author_pubkey": pub, "payload": {"t": f"hi {_n}"},
          "previous_hash": "0x" + "1" * 64}
    if use_ms:
        ev["ts"] = 1793042651190 + _n
    else:
        ev["timestamp"] = 1793042651.25 + _n
    ev["signature"] = sig.sign_event(key, ev)
    return ev


class AllowlistTests(unittest.TestCase):
    def tearDown(self):
        daemon.STATE.trusted_keys = None

    def allow(self, *keys):
        f = _TMP / "trusted.json"
        f.write_text(json.dumps({"keys": list(keys)}))
        daemon.STATE.trusted_keys = sig.load_trusted_keys(str(f))

    def test_trusted_key_accepted(self):
        self.allow(ALICE.upper())  # case-insensitive
        body, code = daemon.process_and_store_event(signed(alice, ALICE), origin_peer=PEER)
        self.assertEqual(code, 200, body)

    def test_untrusted_key_403(self):
        self.allow(ALICE)
        body, code = daemon.process_and_store_event(signed(mallory, MALLORY), origin_peer=PEER)
        self.assertEqual(code, 403, body)

    def test_bad_signature_still_401_before_trust(self):
        self.allow(ALICE)
        ev = signed(alice, ALICE)
        ev["payload"] = {"t": "edited"}
        _, code = daemon.process_and_store_event(ev, origin_peer=PEER)
        self.assertEqual(code, 401)

    def test_no_allowlist_accepts_any_valid_signature(self):
        daemon.STATE.trusted_keys = None
        _, code = daemon.process_and_store_event(signed(mallory, MALLORY), origin_peer=PEER)
        self.assertEqual(code, 200)

    def test_env_unset_means_no_allowlist(self):
        self.assertIsNone(sig.load_trusted_keys())

    def test_plain_list_file_and_bad_files(self):
        f = _TMP / "list.json"
        f.write_text(json.dumps([ALICE]))
        self.assertEqual(sig.load_trusted_keys(str(f)), frozenset({ALICE}))
        f.write_text(json.dumps(["not-hex"]))
        with self.assertRaises(ValueError):
            sig.load_trusted_keys(str(f))
        with self.assertRaises(FileNotFoundError):
            sig.load_trusted_keys(str(_TMP / "missing.json"))


class TimestampTests(unittest.TestCase):
    def test_int_ms_canonical_round_trip(self):
        ev = {"action": "A", "author_pubkey": ALICE, "payload": {"x": 1},
              "previous_hash": "0x" + "0" * 64, "ts": 1793042651190}
        raw = sig.canonical_event_bytes(ev)
        self.assertIn(b'"ts":1793042651190', raw)
        self.assertNotIn(b"timestamp", raw)
        back = json.loads(raw)
        self.assertIsInstance(back["ts"], int)
        self.assertEqual(sig.canonical_event_bytes(back), raw)
        ev["signature"] = sig.sign_event(alice, ev)
        self.assertTrue(sig.verify_event(json.loads(json.dumps(ev))))  # survives the wire
        self.assertFalse(sig.verify_event(dict(ev, ts=ev["ts"] + 1)))
        self.assertFalse(sig.verify_event(dict(ev, ts=float(ev["ts"]))))  # float ms is not int ms

    def test_ms_peer_event_accepted_and_stored_exact(self):
        ev = json.loads(json.dumps(signed(alice, ALICE, use_ms=True)))
        body, code = daemon.process_and_store_event(ev, origin_peer=PEER)
        self.assertEqual(code, 200, body)
        self.assertEqual(body["ts"], ev["ts"])

    def test_legacy_float_peer_event_still_verifies(self):
        body, code = daemon.process_and_store_event(signed(alice, ALICE, use_ms=False), origin_peer=PEER)
        self.assertEqual(code, 200, body)
        self.assertIn("timestamp", body)

    def test_both_or_bad_ts_rejected(self):
        ev = signed(alice, ALICE)
        _, code = daemon.process_and_store_event(dict(ev, timestamp=1.0), origin_peer=PEER)
        self.assertEqual(code, 400)
        _, code = daemon.process_and_store_event(dict(ev, ts=1.5), origin_peer=PEER)
        self.assertEqual(code, 400)
        _, code = daemon.process_and_store_event(dict(ev, ts=True), origin_peer=PEER)
        self.assertEqual(code, 400)

    def test_local_event_emits_int_ms(self):
        body, code = daemon.process_and_store_event({"action": "LOCAL", "payload": {"x": 1}})
        self.assertEqual(code, 200, body)
        self.assertIsInstance(body["ts"], int)
        self.assertNotIn("timestamp", body)

    def test_dart_interop_vectors_unchanged(self):
        self.assertEqual(sig.canonical_event_bytes(DART_EVENT).decode(), DART_CANONICAL)
        self.assertEqual(daemon.compute_canonical_event_id(
            DART_EVENT["action"], DART_PUB, DART_EVENT["payload"], DART_EVENT["previous_hash"],
            DART_EVENT["timestamp"]), DART_ID)
        self.assertTrue(sig.verify_event(dict(DART_EVENT, signature=DART_SIG)))
        self.assertEqual(sig.canonical_bytes(DART_EVENT["action"], DART_PUB, DART_EVENT["payload"],
                                             DART_EVENT["previous_hash"], DART_EVENT["timestamp"]).decode(),
                         DART_CANONICAL)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Signed UDP 9101 beacons (issue #7).

Run: python -m unittest tests/test_signed_beacons.py -v   (no daemon needed)
"""
import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ADMIN = Path(__file__).resolve().parent.parent / "Admin"
sys.path.insert(0, str(ADMIN))

_TMP = Path(tempfile.mkdtemp(prefix="omni_beacon_test_"))
os.environ["HOME"] = str(_TMP)
os.environ.pop("OMNI_TRUSTED_KEYS_FILE", None)
os.environ.pop("OMNI_REQUIRE_SIGNED_BEACONS", None)
os.environ["OMNI_MESH_ID"] = "beacon-test"
os.chdir(_TMP)

import omni_signing as sig  # noqa: E402
daemon = importlib.import_module("omni_live_daemon_server")  # noqa: E402

peer_key = sig.load_or_create_key(_TMP / "peer.key")
PEER = sig.pubkey_hex(peer_key)


def signed_beacon(key=peer_key, node_id=PEER, ts=None, **over):
    msg = {"type": "OMNI_P2P_BEACON", "node_id": node_id, "mesh_id": "beacon-test",
           "ip": "10.0.0.50", "port": 5005, "transport": "UDP_LAN",
           "ts": daemon.now_ms() if ts is None else ts}
    msg.update(over)
    msg["sig"] = key.sign(daemon._beacon_bytes(msg)).hex()
    return msg


class SignedBeaconTests(unittest.TestCase):
    def setUp(self):
        daemon.STATE.active_peers.clear()
        self._trusted = daemon.STATE.trusted_keys

    def tearDown(self):
        daemon.STATE.trusted_keys = self._trusted

    def test_own_beacon_is_signed_and_verifies(self):
        b = daemon.build_beacon()
        self.assertIn("sig", b)
        self.assertTrue(daemon.beacon_signature_ok(b))

    def test_valid_signed_beacon_accepted(self):
        self.assertTrue(daemon.handle_discovery_packet(signed_beacon(), "10.0.0.50"))

    def test_tampered_port_rejected(self):
        b = signed_beacon()
        b["port"] = 6666
        self.assertFalse(daemon.handle_discovery_packet(b, "10.0.0.51"))

    def test_signature_from_other_key_rejected(self):
        other = sig.load_or_create_key(_TMP / "other.key")
        self.assertFalse(daemon.handle_discovery_packet(signed_beacon(key=other), "10.0.0.52"))

    def test_stale_beacon_replay_rejected(self):
        old = signed_beacon(ts=daemon.now_ms() - 5 * 60_000)
        self.assertFalse(daemon.handle_discovery_packet(old, "10.0.0.53"))

    def test_event_signature_cannot_be_reused_as_beacon(self):
        b = signed_beacon()
        ev_sig = peer_key.sign(daemon._beacon_bytes(b)[len(daemon.BEACON_DOMAIN):]).hex()
        b["sig"] = ev_sig
        self.assertFalse(daemon.beacon_signature_ok(b))

    def test_allowlist_requires_trusted_signed_beacon(self):
        daemon.STATE.trusted_keys = {PEER}
        self.assertTrue(daemon.handle_discovery_packet(signed_beacon(), "10.0.0.54"))
        unsigned = {k: v for k, v in signed_beacon().items() if k != "sig"}
        self.assertFalse(daemon.handle_discovery_packet(unsigned, "10.0.0.55"))
        stranger = sig.load_or_create_key(_TMP / "stranger.key")
        self.assertFalse(daemon.handle_discovery_packet(
            signed_beacon(key=stranger, node_id=sig.pubkey_hex(stranger)), "10.0.0.56"))

    def test_unsigned_legacy_beacon_accepted_without_allowlist(self):
        daemon.STATE.trusted_keys = None
        legacy = {"type": "OMNI_P2P_BEACON", "node_id": "e" * 64, "mesh_id": "beacon-test", "port": 5005}
        self.assertTrue(daemon.handle_discovery_packet(legacy, "10.0.0.57"))

    def test_require_signed_flag_rejects_unsigned(self):
        daemon.STATE.trusted_keys = None
        legacy = {"type": "OMNI_P2P_BEACON", "node_id": "d" * 64, "mesh_id": "beacon-test", "port": 5005}
        with mock.patch.object(daemon, "REQUIRE_SIGNED_BEACONS", True):
            self.assertFalse(daemon.handle_discovery_packet(legacy, "10.0.0.58"))

    def test_bad_beacon_does_not_evict_existing_peer(self):
        daemon.handle_discovery_packet(signed_beacon(), "10.0.0.59")
        forged = signed_beacon()
        forged["sig"] = "00" * 64
        daemon.handle_discovery_packet(forged, "10.0.0.59")
        self.assertIn("10.0.0.59", daemon.STATE.active_peers)


if __name__ == "__main__":
    unittest.main(verbosity=2)

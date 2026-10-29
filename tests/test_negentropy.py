"""Range-based set reconciliation (Admin/omni_negentropy.py, negentropy protocol v1).

Run: python -m unittest tests/test_negentropy.py -v   (pure Python, no daemon, no network)

Optional interop check against the negentropy JS reference implementation: set
NEGENTROPY_JS_HARNESS=/path/to/negentropy/test/js/harness.js (needs node). Skipped otherwise; the
pinned vectors below were taken from that harness.
"""
import hashlib
import os
import random
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Admin"))
import omni_negentropy as ng  # noqa: E402

BASE_TS = 1793042651   # seconds


def _id(n) -> bytes:
    return hashlib.sha256(f"omni-event-{n}".encode()).digest()


def _items(ns, ts_fn=lambda n: BASE_TS + n // 3):
    return [(ts_fn(n), _id(n)) for n in ns]


def _ids(items):
    return {i for _, i in items}


class ReconcileTests(unittest.TestCase):
    def check(self, client, server, max_rounds=None):
        have, need, rounds, sent = ng.reconcile_local(ng.Storage(client), ng.Storage(server))
        self.assertEqual(set(have), _ids(client) - _ids(server))
        self.assertEqual(set(need), _ids(server) - _ids(client))
        self.assertEqual(len(have), len(set(have)))   # no duplicates without frame limits
        self.assertEqual(len(need), len(set(need)))
        if max_rounds is not None:
            self.assertLessEqual(rounds, max_rounds)
        return have, need, rounds, sent

    def test_identical_sets(self):
        for n in (1, 10, 31, 32, 100, 1000):
            items = _items(range(n))
            have, need, rounds, _ = self.check(items, list(items))
            self.assertEqual((have, need, rounds), ([], [], 1), n)

    def test_empty_sets(self):
        self.check([], [], max_rounds=1)
        self.check(_items(range(50)), [], max_rounds=2)
        self.check([], _items(range(50)), max_rounds=2)
        self.check([], _items(range(1000)), max_rounds=3)

    def test_disjoint_sets(self):
        self.check(_items(range(0, 40)), _items(range(1000, 1040)))
        self.check(_items(range(0, 500)), _items(range(1000, 1500)))

    def test_partial_overlap(self):
        self.check(_items(range(0, 300)), _items(range(150, 450)))
        rnd = random.Random(42)
        everything = list(range(2000))
        a = [n for n in everything if rnd.random() < 0.8]
        b = [n for n in everything if rnd.random() < 0.8]
        self.check(_items(a), _items(b))

    def test_1000_events_few_differences_few_round_trips(self):
        server = _items(range(1000))
        rnd = random.Random(7)
        drop = set(rnd.sample(range(1000), 5))
        client = [it for n, it in enumerate(server) if n not in drop] + _items(range(5000, 5003))
        have, need, rounds, sent = self.check(client, server, max_rounds=3)
        self.assertEqual(len(need), 5)
        self.assertEqual(len(have), 3)
        # Far less than shipping every id (1000 * 32 bytes) one way.
        self.assertLess(sent, 1000 * 32 // 2)

    def test_1000_events_node_offline_for_a_while(self):
        """The catch-up case: the reconnecting node lacks the newest 200 events."""
        server = _items(range(1000))
        client = server[:800]
        have, need, rounds, _ = self.check(client, server, max_rounds=3)
        self.assertEqual((len(have), len(need)), (0, 200))

    def test_same_timestamp_uses_id_prefix_bounds(self):
        items = _items(range(600), ts_fn=lambda n: BASE_TS)
        self.check(items[::2], items, max_rounds=4)
        msg = ng.Negentropy(ng.Storage(items)).initiate()
        self.assertEqual(msg[0], ng.PROTOCOL_VERSION)

    def test_duplicate_items_are_collapsed(self):
        items = _items(range(10))
        self.assertEqual(len(ng.Storage(items + items)), 10)


class WireFormatTests(unittest.TestCase):
    def test_varint(self):
        cases = {0: "00", 1: "01", 127: "7f", 128: "8100", 300: "822c", 2 ** 64 - 1: "81ffffffffffffffff7f"}
        for n, hx in cases.items():
            self.assertEqual(ng.encode_varint(n).hex(), hx)
            self.assertEqual(ng._Reader(bytes.fromhex(hx)).varint(), n)

    def test_fingerprint_is_order_independent(self):
        ids = [_id(n) for n in range(20)]
        a = ng.Storage([(1, i) for i in ids])
        b = ng.Storage([(1, i) for i in reversed(ids)])
        self.assertEqual(a.fingerprint(0, 20), b.fingerprint(0, 20))
        self.assertNotEqual(a.fingerprint(0, 20), a.fingerprint(0, 19))

    # Vectors from the negentropy JS reference (hoytech/negentropy js/Negentropy.js via
    # test/js/harness.js), items: ts = 1700000000 + i // 3, id = sha256(str(i)).
    @staticmethod
    def _ref_items(n):
        return [(1700000000 + i // 3, hashlib.sha256(str(i).encode()).digest()) for i in range(n)]

    def test_initiate_matches_reference_vectors(self):
        m10 = ng.Negentropy(ng.Storage(self._ref_items(10))).initiate()
        self.assertEqual(len(m10), 325)
        self.assertEqual(hashlib.sha256(m10).hexdigest(),
                         "f8a498a85f1057a0fc2eab92723ab040b4cdd97969d8afdaf7aedb2a9485d2c2")
        m100 = ng.Negentropy(ng.Storage(self._ref_items(100))).initiate()
        self.assertEqual(len(m100), 323)
        self.assertEqual(hashlib.sha256(m100).hexdigest(),
                         "fc3f86b9e438d163e98fe85258c279bbda12f4cb0bd03275c7c6f4820cf8b889")

    def test_server_reply_matches_reference_vector(self):
        items = self._ref_items(100)
        server = ng.Negentropy(ng.Storage([x for k, x in enumerate(items) if k % 7]))
        reply, _, _ = server.reconcile(ng.Negentropy(ng.Storage(items)).initiate())
        self.assertEqual(len(reply), 2417)
        self.assertEqual(hashlib.sha256(reply).hexdigest(),
                         "040e1678692169bf68b3f84277e73f748b11b7d91e579792c83a276d0811cfd7")

    def test_unsupported_version_answered_with_ours(self):
        out, have, need = ng.Negentropy(ng.Storage([])).reconcile(b"\x62")
        self.assertEqual(out, b"\x61")
        client = ng.Negentropy(ng.Storage([]))
        client.initiate()
        with self.assertRaises(ValueError):
            client.reconcile(b"\x62")

    def test_malformed_messages_raise_value_error(self):
        server = ng.Negentropy(ng.Storage(_items(range(5))))
        for bad in ("", "61ff", "610000", "61000001aabb", "6100000205", "61000003", "610021"):
            with self.assertRaises(ValueError, msg=bad):
                server.reconcile(bytes.fromhex(bad))


@unittest.skipUnless(os.environ.get("NEGENTROPY_JS_HARNESS"), "set NEGENTROPY_JS_HARNESS to run interop")
class JsReferenceInteropTests(unittest.TestCase):
    def _js_server_reply(self, items, msg):
        inp = "".join(f"item,{t},{i.hex()}\n" for t, i in items) + f"seal\nmsg,{msg.hex()}\n"
        out = subprocess.run(["node", os.environ["NEGENTROPY_JS_HARNESS"]], input=inp,
                             capture_output=True, text=True, timeout=30).stdout.strip().splitlines()
        return bytes.fromhex(out[-1][4:])

    def test_python_client_js_server(self):
        server = _items(range(1000))
        client = server[:900] + _items(range(3000, 3010))
        c = ng.Negentropy(ng.Storage(client))
        msg, have, need = c.initiate(), [], []
        while msg is not None:
            reply = self._js_server_reply(server, msg)
            self.assertEqual(reply, ng.Negentropy(ng.Storage(server)).reconcile(msg)[0])
            msg, h, n = c.reconcile(reply)
            have += h
            need += n
        self.assertEqual(set(have), _ids(client) - _ids(server))
        self.assertEqual(set(need), _ids(server) - _ids(client))


if __name__ == "__main__":
    unittest.main()

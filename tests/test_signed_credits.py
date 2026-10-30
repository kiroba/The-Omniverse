"""Daemon v8.15.0: signed credit transfers (POST /api/credits/send) and node-local double-spend rules.

Run: python3 -m unittest tests.test_signed_credits
"""
import json
import secrets
import shutil
import socket
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daemon_harness import Daemon, Key, daemon_module, http, now_ms  # noqa: E402


def signed_transfer(key: Key, to: str, amount: int, kind="transfer", memo="", ref=None, nonce=None, ts=None,
                    signer: Key = None) -> dict:
    msg = {"type": "omni.credits.transfer.v1", "from": key.pub, "to": to, "amount": amount, "kind": kind,
           "memo": memo, "nonce": nonce or secrets.token_hex(16), "ts": ts if ts is not None else now_ms()}
    if ref is not None:
        msg["ref"] = ref
    raw = json.dumps(msg, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return dict(msg, sig=(signer or key).sign(raw))


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


REMOTE_IP = _local_ip()


class Unit(unittest.TestCase):
    def test_forged_auth_in_an_entry_fails_replay_validation(self):
        d = daemon_module()
        a, b = Key(), Key()
        t = signed_transfer(a, b.pub, 10)
        entry = {"kind": "transfer", "from": a.pub, "to": b.pub, "amount": 10, "fee": 0, "memo": "",
                 "test_only": True, "auth": {k: t[k] for k in ("type", "nonce", "ts", "sig")}}
        self.assertEqual(d.validate_credit_payload(dict(entry)), entry)
        with self.assertRaises(ValueError):
            d.validate_credit_payload(dict(entry, amount=11))      # signed 10, entry says 11
        with self.assertRaises(ValueError):
            d.validate_credit_payload(dict(entry, to=Key().pub))   # redirected
        with self.assertRaises(ValueError):
            d.validate_credit_payload({**entry, "kind": "tip"})     # tip needs ref


class LiveSignedCredits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_signed_credits_"))
        cls.d = Daemon(cls.tmp, "scredits", env={"OMNI_TREASURY_FEE_BPS": "200"}).start()

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def bal(self, pk):
        return self.d.get("/api/credits/balance", {"pubkey": pk})[1]["balance"]

    def test_send_replay_and_double_spend(self):
        a, b = Key(), Key()
        t = signed_transfer(a, b.pub, 250, memo="for lunch")
        code, r = self.d.post("/api/credits/send", t)
        self.assertEqual(code, 200, r)
        self.assertEqual(r["balance"], 750)   # welcome 1000 issued on first send, then -250
        self.assertEqual(r["entry"]["fee"], 5)   # 2% of 250, out of what b gets
        self.assertEqual(self.bal(b.pub), 1000 + 245)
        # Identical retry (network glitch): applied once, answered idempotently.
        code, r2 = self.d.post("/api/credits/send", t)
        self.assertEqual((code, r2["result"], r2["event_id"]), (200, "ALREADY_APPLIED", r["event_id"]))
        self.assertEqual(self.bal(a.pub), 750)
        # Same nonce, different content: refused.
        t2 = signed_transfer(a, b.pub, 1, nonce=t["nonce"])
        self.assertEqual(self.d.post("/api/credits/send", t2)[0], 409)
        # History carries the signature, so the ledger proves a.pub authorized it.
        code, h = self.d.get("/api/credits/history", {"pubkey": a.pub})
        sent = [e for e in h["entries"] if e["kind"] == "transfer"][0]
        self.assertEqual((sent["auth"]["sig"], sent["delta"]), (t["sig"], -250))

    def test_rejections(self):
        a, b = Key(), Key()
        self.assertEqual(self.d.post("/api/credits/send", signed_transfer(a, b.pub, 5, signer=b))[0], 401)
        forged = dict(signed_transfer(a, b.pub, 5), amount=500)
        self.assertEqual(self.d.post("/api/credits/send", forged)[0], 401)
        self.assertEqual(self.d.post("/api/credits/send", signed_transfer(a, b.pub, 5, ts=now_ms() - 3_600_000))[0], 401)
        self.assertEqual(self.d.post("/api/credits/send", signed_transfer(a, b.pub, 5, memo=" padded "))[0], 400)
        self.assertEqual(self.d.post("/api/credits/send", signed_transfer(a, b.pub, 5, kind="tip"))[0], 400)
        self.assertEqual(self.d.post("/api/credits/send", signed_transfer(a, b.pub, 5, kind="grant"))[0], 400)
        self.assertEqual(self.d.post("/api/credits/send", signed_transfer(a, a.pub, 5))[0], 400)
        bad = signed_transfer(a, b.pub, 5)
        bad.pop("nonce")
        self.assertEqual(self.d.post("/api/credits/send", bad)[0], 400)
        self.assertEqual(self.d.post("/api/credits/send", signed_transfer(a, b.pub, 5000))[0], 409)   # overdraft

    def test_tip_with_post_ref(self):
        a, b = Key(), Key()
        post_id = "0x" + "a" * 64
        code, r = self.d.post("/api/credits/send", signed_transfer(a, b.pub, 20, kind="tip", ref=post_id))
        self.assertEqual(code, 200, r)
        self.assertEqual((r["entry"]["kind"], r["entry"]["ref"]), ("tip", post_id))
        code, s = self.d.get("/api/telemetry/summary")
        self.assertGreaterEqual(s["finance"]["entries_by_kind"]["tip"], 1)

    def test_concurrent_sends_cannot_overspend(self):
        a, b = Key(), Key()
        self.assertEqual(self.bal(a.pub), 1000)
        results = []
        def go():
            results.append(self.d.post("/api/credits/send", signed_transfer(a, b.pub, 300))[0])
        threads = [threading.Thread(target=go) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sorted(results), [200] * 3 + [409] * 5)
        self.assertEqual(self.bal(a.pub), 100)

    def test_tampered_auth_in_db_fails_integrity(self):
        a, b = Key(), Key()
        code, r = self.d.post("/api/credits/send", signed_transfer(a, b.pub, 1))
        self.assertEqual(code, 200, r)
        tmp_db = self.tmp / "tamper_copy.db"
        conn = sqlite3.connect(str(self.d.db))
        conn.execute("VACUUM INTO ?", (str(tmp_db),))
        conn.close()
        conn = sqlite3.connect(str(tmp_db))
        pj = conn.execute("SELECT payload_json FROM events WHERE event_id = ?", (r["event_id"],)).fetchone()[0]
        p = json.loads(pj)
        p["amount"] = 2
        conn.execute("UPDATE events SET payload_json = ? WHERE event_id = ?", (json.dumps(p), r["event_id"]))
        conn.commit()
        conn.close()
        d = daemon_module()
        saved = d.STATE.node_id
        d.STATE.node_id = self.d.node_id
        try:
            with self.assertRaises(d.LedgerIntegrityError):
                d.replay_credit_ledger(tmp_db)
        finally:
            d.STATE.node_id = saved


@unittest.skipIf(REMOTE_IP.startswith("127."), "no non-loopback IP on this machine")
class RemoteAndRequireSigned(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_signed_credits_remote_"))
        cls.d = Daemon(cls.tmp, "scremote", remote=True, env={"OMNI_CREDITS_REQUIRE_SIGNED": "1"}).start()
        cls.auth = {"Authorization": "Bearer " + (cls.d.home / ".omni" / "hub_token").read_text().strip()}
        cls.base = f"http://{REMOTE_IP}:{cls.d.ipc_port}"

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_remote_balance_does_not_write_then_signed_send(self):
        a, b = Key(), Key()
        before = self.d.event_count()
        code, r = http(f"{self.base}/api/credits/balance?pubkey={a.pub}", headers=self.auth)
        self.assertEqual(code, 200, r)
        self.assertEqual((r["balance"], r["available"], r["welcome_pending"]), (0, 1000, True))
        self.assertEqual(self.d.event_count(), before)
        code, r = http(f"{self.base}/api/credits/send", signed_transfer(a, b.pub, 40), headers=self.auth)
        self.assertEqual((code, r["balance"]), (200, 960), r)
        code, r = http(f"{self.base}/api/credits/history?pubkey={a.pub}", headers=self.auth)
        self.assertEqual(code, 200)
        # Unsigned and admin paths stay loopback only.
        self.assertEqual(http(f"{self.base}/api/credits/transfer", {"from": a.pub, "to": b.pub, "amount": 1},
                              headers=self.auth)[0], 403)
        self.assertEqual(http(f"{self.base}/api/credits/grant", {"to": a.pub, "amount": 1}, headers=self.auth)[0], 403)

    def test_require_signed_turns_off_unsigned_transfer(self):
        a, b = Key(), Key()
        code, r = self.d.post("/api/credits/transfer", {"from": a.pub, "to": b.pub, "amount": 1})
        self.assertEqual(code, 403, r)
        self.assertIn("/api/credits/send", r["message"])


if __name__ == "__main__":
    unittest.main()

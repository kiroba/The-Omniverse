"""Omni Credits TEST ledger (daemon v8.10.0): /api/credits/* on :5000, entries as signed chain events.

Run: python -m unittest tests/test_credits_ledger.py -v
Starts a real daemon as a subprocess on free temp ports (OMNI_*_PORT overrides), with HOME and cwd in
temp dirs and OMNI_TREASURY_FEE_BPS=250 (2.5%). Same harness pattern as tests/test_bug_reports.py.
"""
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daemon_version import DAEMON_VERSION  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ADMIN = ROOT / "Admin"

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_PYPATH = os.pathsep.join(p for p in [os.environ.get("PYTHONPATH", ""), str(ADMIN)] if p)
FEE_BPS = 250


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


REMOTE_IP = _local_ip()


def _http(url, data=None, raw=None, timeout=10, headers=None):
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


def _pk(n: int) -> str:
    return f"{n:064x}"


class Daemon:
    def __init__(self, root: Path, name: str, fee_bps: int = FEE_BPS, remote: bool = False):
        self.home, self.cwd = root / f"home_{name}", root / f"run_{name}"
        self.home.mkdir(parents=True)
        self.cwd.mkdir(parents=True)
        self.ports = {"OMNI_TELEMETRY_PORT": _free_port(), "OMNI_IPC_PORT": _free_port(),
                      "OMNI_P2P_PORT": _free_port(), "OMNI_UDP_PORT": _free_port(socket.SOCK_DGRAM)}
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home), PYTHONPATH=_PYPATH,
                        OMNI_MESH_ID=f"credits-{name}", OMNI_CATCHUP_INTERVAL="0",
                        OMNI_CATCHUP_STARTUP_DELAY="3600", NO_PROXY="*", OMNI_TREASURY_FEE_BPS=str(fee_bps),
                        **{k: str(v) for k, v in self.ports.items()})
        for k in ("OMNI_TRUSTED_KEYS_FILE", "OMNI_LEGACY_FLOAT_TS", "OMNI_SYNC_PEERS", "OMNI_HUB_TOKEN_FILE",
                  "OMNI_HUB_REMOTE", "OMNI_HUB_BIND"):
            self.env.pop(k, None)
        if remote:
            self.env.update(OMNI_HUB_REMOTE="1", OMNI_HUB_BIND="0.0.0.0")
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

    def balance(self, pubkey):
        return _http(f"{self.ipc}/api/credits/balance?pubkey={urllib.parse.quote(pubkey)}")

    def history(self, pubkey, limit=50):
        return _http(f"{self.ipc}/api/credits/history?pubkey={urllib.parse.quote(pubkey)}&limit={limit}")

    def transfer(self, body):
        return _http(f"{self.ipc}/api/credits/transfer", body)

    def grant(self, body):
        return _http(f"{self.ipc}/api/credits/grant", body)


class CreditsLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_credits_"))
        cls.d = Daemon(cls.tmp, "local")
        cls.d.start()

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_version(self):
        self.assertEqual(self.d.version, DAEMON_VERSION)

    def test_grant_once(self):
        a = _pk(0xA1)
        code, b = self.d.balance(a)
        self.assertEqual(code, 200, b)
        self.assertEqual(b["balance"], 1000)
        self.assertTrue(b["test_only"])
        for _ in range(3):   # repeat lookups never grant again
            _, b = self.d.balance(a)
            self.assertEqual(b["balance"], 1000)
        _, h = self.d.history(a)
        grants = [e for e in h["entries"] if e["kind"] == "grant"]
        self.assertEqual(len(grants), 1)
        self.assertEqual(grants[0]["amount"], 1000)
        self.assertEqual(grants[0]["from"], "treasury")
        self.assertIs(grants[0]["test_only"], True)
        # stored as a node-signed credit_entry chain event
        conn = sqlite3.connect(str(self.d.db))
        try:
            row = conn.execute("SELECT action, author_pubkey, signature FROM events WHERE event_id=?",
                               (grants[0]["event_id"],)).fetchone()
        finally:
            conn.close()
        self.assertEqual(row[0], "credit_entry")
        self.assertEqual(row[1], self.d.node_id)
        self.assertTrue(row[2])
        # uppercase hex is the same identity
        _, b = self.d.balance(a.upper())
        self.assertEqual(b["balance"], 1000)

    def test_transfer_with_fee_to_treasury(self):
        a, b = _pk(0xB1), _pk(0xB2)
        _, t0 = self.d.balance("treasury")
        code, r = self.d.transfer({"from": a, "to": b, "amount": 400, "memo": "sticker pack"})
        self.assertEqual(code, 200, r)
        fee = 400 * FEE_BPS // 10000   # 10
        self.assertEqual(r["entry"]["fee"], fee)
        self.assertEqual(r["entry"]["kind"], "transfer")
        self.assertEqual(r["balance"], 600)
        self.assertEqual(self.d.balance(a)[1]["balance"], 600)
        # b: welcome grant on first lookup + 390 received
        self.assertEqual(self.d.balance(b)[1]["balance"], 1000 + 400 - fee)
        self.assertEqual(self.d.balance("treasury")[1]["balance"], t0["balance"] + fee)
        # purchase straight to treasury carries no fee
        code, r = self.d.transfer({"from": a, "to": "treasury", "amount": 100, "kind": "purchase"})
        self.assertEqual(code, 200, r)
        self.assertEqual(r["entry"]["fee"], 0)
        self.assertEqual(self.d.balance(a)[1]["balance"], 500)
        _, h = self.d.history(a, limit=1)
        self.assertEqual(h["entries"][0]["kind"], "purchase")
        self.assertEqual(h["entries"][0]["balance_after"], 500)
        self.assertTrue(h["has_more"])

    def test_overdraft_and_bad_amounts_rejected(self):
        a, b = _pk(0xC1), _pk(0xC2)
        code, r = self.d.transfer({"from": a, "to": b, "amount": 1001})
        self.assertEqual(code, 409, r)
        self.assertEqual(r["balance"], 1000)
        self.assertEqual(self.d.balance(a)[1]["balance"], 1000)
        bad = [
            {"from": a, "to": b, "amount": 10.5},
            {"from": a, "to": b, "amount": 10.0},
            {"from": a, "to": b, "amount": "10"},
            {"from": a, "to": b, "amount": True},
            {"from": a, "to": b, "amount": 0},
            {"from": a, "to": b, "amount": -5},
            {"from": a, "to": b, "amount": 1_000_001},
            {"from": a, "to": a, "amount": 1},
            {"from": "treasury", "to": b, "amount": 1},
            {"from": "nothex", "to": b, "amount": 1},
            {"from": a, "to": b, "amount": 1, "fee": 0},          # client can't set the fee
            {"from": a, "to": b, "amount": 1, "kind": "grant"},
        ]
        for body in bad:
            code, r = self.d.transfer(body)
            self.assertEqual(code, 400, (body, r))
        self.assertEqual(self.d.grant({"to": b, "amount": 1_000_001})[0], 400)
        self.assertEqual(self.d.grant({"to": b, "amount": 2.5})[0], 400)
        self.assertEqual(self.d.balance(a)[1]["balance"], 1000)
        # credit entries can't be forged through the generic append path
        code, r = _http(f"{self.d.ipc}/api/events/append",
                        {"action": "credit_entry", "payload": {"kind": "grant", "from": "treasury", "to": a,
                                                               "amount": 999999, "fee": 0, "memo": "",
                                                               "test_only": True}})
        self.assertEqual(code, 403, r)
        self.assertEqual(self.d.balance(a)[1]["balance"], 1000)

    def test_admin_grant_and_reset(self):
        a = _pk(0xD1)
        code, r = self.d.grant({"to": a, "amount": 250, "memo": "tester bonus"})
        self.assertEqual(code, 200, r)
        # welcome grant still issued once on first lookup, on top of the admin grant
        self.assertEqual(self.d.balance(a)[1]["balance"], 1250)
        code, r = self.d.grant({"kind": "reset", "pubkey": a})
        self.assertEqual(code, 200, r)
        self.assertEqual(r["entry"]["amount"], 1250)
        self.assertEqual(self.d.balance(a)[1]["balance"], 0)   # no second welcome grant after reset
        code, r = self.d.grant({"kind": "reset", "pubkey": a})
        self.assertEqual(r.get("result"), "NOTHING_TO_RESET")

    def test_replayed_balances_match(self):
        accts = [_pk(0xE1), _pk(0xE2), _pk(0xE3)]
        for x in accts:
            self.d.balance(x)
        moves = [(0, 1, 120), (1, 2, 333), (2, 0, 47), (0, 2, 26)]
        for f, t, amt in moves:
            code, r = self.d.transfer({"from": accts[f], "to": accts[t], "amount": amt})
            self.assertEqual(code, 200, r)
        # independent replay from the raw event feed (every entry verified)
        _, feed = _http(f"{self.d.ipc}/api/events/feed?type=credit_entry&limit=200")
        self.assertFalse(feed["has_more"])
        bal = {}
        for e in reversed(feed["events"]):
            self.assertTrue(e["verified"], e["event_id"])
            p = e["payload"]
            if p["from"] != "treasury":
                bal[p["from"]] = bal.get(p["from"], 0) - p["amount"]
            bal[p["to"]] = bal.get(p["to"], 0) + p["amount"] - p["fee"]
            if p["fee"]:
                bal["treasury"] = bal.get("treasury", 0) + p["fee"]
        for x in accts + ["treasury"]:
            self.assertEqual(self.d.balance(x)[1]["balance"], bal.get(x, 0), x)
        self.assertEqual(sum(self.d.balance(x)[1]["balance"] for x in accts) +
                         sum(m[2] * FEE_BPS // 10000 for m in moves), 3000)


class TamperTests(unittest.TestCase):
    """Edits a stored entry directly in SQLite; every credits read must then refuse with 409."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="omni_credits_tamper_"))
        self.d = Daemon(self.tmp, "tamper")
        self.d.start()
        self.a, self.b = _pk(0xF1), _pk(0xF2)
        self.assertEqual(self.d.transfer({"from": self.a, "to": self.b, "amount": 100})[0], 200)

    def tearDown(self):
        self.d.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _edit(self, sql_fn):
        conn = sqlite3.connect(str(self.d.db))
        try:
            rid, pj, sig = conn.execute("SELECT id, payload_json, signature FROM events WHERE action='credit_entry' "
                                        "ORDER BY id DESC LIMIT 1").fetchone()
            sql_fn(conn, rid, json.loads(pj), sig)
            conn.commit()
        finally:
            conn.close()

    def _assert_refused(self):
        for code, r in (self.d.balance(self.a), self.d.history(self.b),
                        self.d.transfer({"from": self.a, "to": self.b, "amount": 1})):
            self.assertEqual(code, 409, r)
            self.assertEqual(r.get("integrity"), "FAILED", r)

    def test_tampered_amount_fails_verification(self):
        self._edit(lambda c, rid, p, sig: c.execute("UPDATE events SET payload_json=? WHERE id=?",
                                                    (json.dumps(dict(p, amount=900)), rid)))
        self._assert_refused()

    def test_forged_signature_fails_verification(self):
        bad = "00" * 64   # well-formed hex, wrong signature
        self._edit(lambda c, rid, p, sig: c.execute("UPDATE events SET signature=? WHERE id=?", (bad, rid)))
        self._assert_refused()


@unittest.skipIf(REMOTE_IP.startswith("127."), "no non-loopback IP on this machine")
class RemoteHubCreditsTests(unittest.TestCase):
    """Credits endpoints stay loopback only even with remote hub on and a valid bearer token."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_credits_remote_"))
        cls.d = Daemon(cls.tmp, "remote", remote=True)
        cls.d.start()
        cls.auth = {"Authorization": "Bearer " + (cls.d.home / ".omni" / "hub_token").read_text().strip()}
        cls.remote = f"http://{REMOTE_IP}:{cls.d.ports['OMNI_IPC_PORT']}"

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_credits_are_loopback_only(self):
        """Unsigned writes stay loopback only. Since v8.15.0 balance/history are readable remotely
        (read-only: a remote balance lookup never issues the welcome grant) and signed sends go to
        /api/credits/send (tests/test_signed_credits.py)."""
        a, b = _pk(0x51), _pk(0x52)
        code, r = _http(f"{self.remote}/api/credits/balance?pubkey={a}", headers=self.auth)
        self.assertEqual((code, r["balance"], r["welcome_pending"]), (200, 0, True))
        self.assertEqual(_http(f"{self.remote}/api/credits/history?pubkey={a}", headers=self.auth)[0], 200)
        self.assertEqual(_http(f"{self.remote}/api/credits/transfer", {"from": a, "to": b, "amount": 1},
                               headers=self.auth)[0], 403)
        self.assertEqual(_http(f"{self.remote}/api/credits/grant", {"to": a, "amount": 1},
                               headers=self.auth)[0], 403)
        # remote append of a credit_entry (phone-signed shape or not) is refused too
        code, _ = _http(f"{self.remote}/api/events/append", {"action": "credit_entry", "payload": {}},
                        headers=self.auth)
        self.assertEqual(code, 403)
        self.assertEqual(self.d.balance(a)[1]["balance"], 1000)   # loopback still works


if __name__ == "__main__":
    unittest.main()

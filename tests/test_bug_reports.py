"""Bug reports (daemon v8.9.0): POST /api/bugs/report, GET /api/bugs/list, triage utility.

Run: python -m unittest tests/test_bug_reports.py -v
Starts real daemons as subprocesses on free temp ports (OMNI_*_PORT overrides), with HOME and cwd in
temp dirs. The remote-hub test talks to this machine's non-loopback IP and is skipped without one.
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
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADMIN = ROOT / "Admin"
sys.path.insert(0, str(ADMIN))
import omnimind_bug_triage_utility as triage  # noqa: E402

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_PYPATH = os.pathsep.join(p for p in [os.environ.get("PYTHONPATH", ""), str(ADMIN)] if p)


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


def _http(url, data=None, headers=None, raw=None, timeout=5):
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


class Daemon:
    def __init__(self, root: Path, name: str, remote: bool = False):
        self.home, self.cwd = root / f"home_{name}", root / f"run_{name}"
        self.home.mkdir(parents=True)
        self.cwd.mkdir(parents=True)
        self.ports = {"OMNI_TELEMETRY_PORT": _free_port(), "OMNI_IPC_PORT": _free_port(),
                      "OMNI_P2P_PORT": _free_port(), "OMNI_UDP_PORT": _free_port(socket.SOCK_DGRAM)}
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home), PYTHONPATH=_PYPATH,
                        OMNI_MESH_ID=f"bugs-{name}", OMNI_CATCHUP_INTERVAL="0",
                        OMNI_CATCHUP_STARTUP_DELAY="3600", NO_PROXY="*",
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

    def report(self, payload, **kw):
        return _http(f"{self.ipc}/api/bugs/report", payload, **kw)


SAMPLE = {"what_happened": "Feed stays empty after switching Hub to Remote hub", "app": "KickBack",
          "app_version": "0.1.9", "device": "Pixel 6a", "android_version": "14",
          "network": "Tailscale remote", "steps": "1. Settings > Hub\n2. Remote hub\n3. Open feed"}


class BugReportDaemonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_bug_reports_"))
        cls.d = Daemon(cls.tmp, "local")
        cls.d.start()

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_version(self):
        self.assertEqual(self.d.version, "8.10.0")

    def test_post_list_and_triage_verifies(self):
        code, body = self.d.report(SAMPLE)
        self.assertEqual(code, 200, body)
        eid = body["event_id"]
        self.assertRegex(eid, r"^0x[0-9a-f]{64}$")

        code, lst = _http(f"{self.d.ipc}/api/bugs/list?limit=5")
        self.assertEqual(code, 200, lst)
        self.assertGreaterEqual(lst["count"], 1)
        ids = [r["event_id"] for r in lst["reports"]]
        self.assertIn(eid, ids)
        mine = lst["reports"][ids.index(eid)]
        self.assertTrue(mine["verified"])
        self.assertEqual(mine["author_pubkey"], self.d.node_id)
        self.assertEqual(mine["report"]["what_happened"], SAMPLE["what_happened"])
        self.assertEqual(mine["report"]["received_via"], "loopback")
        # newest first
        code, b2 = self.d.report(dict(SAMPLE, what_happened="second report"))
        self.assertEqual(code, 200, b2)
        _, lst2 = _http(f"{self.d.ipc}/api/bugs/list?limit=1")
        self.assertEqual(lst2["count"], 1)
        self.assertEqual(lst2["reports"][0]["event_id"], b2["event_id"])
        self.assertTrue(lst2["has_more"])

        # stored as a normal chain event
        conn = sqlite3.connect(str(self.d.db))
        try:
            row = conn.execute("SELECT action, author_pubkey, signature FROM events WHERE event_id=?", (eid,)).fetchone()
        finally:
            conn.close()
        self.assertEqual(row[0], "bug_report")
        self.assertTrue(row[2])

        rep = triage.show_report(eid, self.d.db)
        self.assertIsNotNone(rep)
        self.assertTrue(rep["hash_ok"])
        self.assertTrue(rep["signature_ok"])
        self.assertEqual(rep["link"], "OK")
        self.assertTrue(rep["valid"])

    def test_bug_reports_show_in_feed_filter(self):
        code, body = self.d.report({"what_happened": "feed filter check"})
        self.assertEqual(code, 200, body)
        _, feed = _http(f"{self.d.ipc}/api/events/feed?type=bug_report&limit=50")
        self.assertIn(body["event_id"], [e["event_id"] for e in feed["events"]])

    def test_invalid_payloads_rejected(self):
        cases = [
            ({}, 400),                                                  # what_happened missing
            ({"what_happened": "   "}, 400),                            # blank
            ({"what_happened": 42}, 400),                               # not a string
            ({"what_happened": "x", "hub_token": "secret"}, 400),       # unknown field
            ({"what_happened": "x", "identity_seed": "abandon abandon"}, 400),
            ({"what_happened": "x" * 4001}, 400),                       # field too long
        ]
        for payload, want in cases:
            code, body = self.d.report(payload)
            self.assertEqual(code, want, (payload if len(str(payload)) < 80 else "long", body))
        code, _ = self.d.report(None, raw=b"{not json")
        self.assertEqual(code, 400)
        code, _ = self.d.report(None, raw=b"[1,2,3]")
        self.assertEqual(code, 400)
        big = json.dumps({"what_happened": "y", "steps": "z" * 9000}).encode()
        code, body = self.d.report(None, raw=big)
        self.assertEqual(code, 413, body)
        code, _ = _http(f"{self.d.ipc}/api/bugs/list?limit=abc")
        self.assertEqual(code, 400)
        code, _ = _http(f"{self.d.ipc}/api/bugs/list?evil=1")
        self.assertEqual(code, 400)
        # nothing rejected was stored
        conn = sqlite3.connect(str(self.d.db))
        try:
            stored = [json.loads(r[0]) for r in conn.execute(
                "SELECT payload_json FROM events WHERE action='bug_report'").fetchall()]
        finally:
            conn.close()
        self.assertFalse(any("hub_token" in p or "identity_seed" in p for p in stored))
        self.assertFalse(any(p.get("what_happened") == "y" for p in stored))


class TriageTamperTests(unittest.TestCase):
    """Triage on a copy of a real daemon DB: duplicates grouped, tampered rows fail verification."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_bug_triage_"))
        d = Daemon(cls.tmp, "triage")
        d.start()
        try:
            cls.ids = []
            for text, device in [("App crashes on launch!", "Pixel 6a"), ("app crashes on  launch", "pixel 6a"),
                                 ("App crashes on launch", "Galaxy A14"), ("Send button does nothing", "Pixel 6a")]:
                code, body = d.report(dict(SAMPLE, what_happened=text, device=device))
                assert code == 200, body
                cls.ids.append(body["event_id"])
            # an ordinary non-bug event in between must not appear in triage
            _http(f"{d.ipc}/api/events/append", {"action": "CHAT", "payload": {"text": "hi"}})
            code, body = d.report({"what_happened": "last one"})
            assert code == 200, body
            cls.ids.append(body["event_id"])
        finally:
            d.stop()
        cls.db = d.db

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _copy(self):
        dst = self.tmp / f"copy_{time.time_ns()}.db"
        src = sqlite3.connect(str(self.db))
        out = sqlite3.connect(str(dst))
        try:
            src.backup(out)
        finally:
            src.close()
            out.close()
        return dst

    def test_summary_groups_duplicates_and_all_valid(self):
        s = triage.summarize(self.db)
        self.assertEqual(s["total"], 5)
        self.assertEqual(s["valid"], 5)
        self.assertEqual(s["invalid"], [])
        top = s["groups"][0]
        self.assertEqual(top["count"], 2)                    # same text+device, case/punctuation-insensitive
        self.assertEqual(set(top["event_ids"]), set(self.ids[:2]))
        self.assertEqual(len(s["groups"]), 4)                # Galaxy A14 crash is its own group
        for r in triage.list_reports(self.db):
            self.assertTrue(r["valid"], r)

    def test_tampered_payload_fails(self):
        db = self._copy()
        conn = sqlite3.connect(str(db))
        try:
            pj = json.loads(conn.execute("SELECT payload_json FROM events WHERE event_id=?", (self.ids[3],)).fetchone()[0])
            pj["what_happened"] = "nothing to see here"
            conn.execute("UPDATE events SET payload_json=? WHERE event_id=?", (json.dumps(pj), self.ids[3]))
            conn.commit()
        finally:
            conn.close()
        rep = triage.show_report(self.ids[3], db)
        self.assertFalse(rep["hash_ok"])
        self.assertFalse(rep["signature_ok"])
        self.assertFalse(rep["valid"])
        self.assertEqual(triage.summarize(db)["invalid"], [self.ids[3]])
        self.assertTrue(triage.show_report(self.ids[2], db)["valid"])  # others untouched

    def test_forged_signature_fails(self):
        db = self._copy()
        conn = sqlite3.connect(str(db))
        try:
            s = conn.execute("SELECT signature FROM events WHERE event_id=?", (self.ids[1],)).fetchone()[0]
            forged = ("0" if s[0] != "0" else "1") + s[1:]
            conn.execute("UPDATE events SET signature=? WHERE event_id=?", (forged, self.ids[1]))
            conn.commit()
        finally:
            conn.close()
        rep = triage.show_report(self.ids[1], db)
        self.assertTrue(rep["hash_ok"])
        self.assertFalse(rep["signature_ok"])
        self.assertFalse(rep["valid"])

    def test_broken_chain_link_fails(self):
        db = self._copy()
        conn = sqlite3.connect(str(db))
        try:   # delete the row a report chains onto: its previous_hash now points at nothing
            prev = conn.execute("SELECT previous_hash FROM events WHERE event_id=?", (self.ids[2],)).fetchone()[0]
            conn.execute("DELETE FROM events WHERE event_id=?", (prev,))
            conn.commit()
        finally:
            conn.close()
        rep = triage.show_report(self.ids[2], db)
        self.assertEqual(rep["link"], "BROKEN")
        self.assertFalse(rep["valid"])

    def test_cli(self):
        env = dict(os.environ, PYTHONPATH=_PYPATH)
        tool = str(ADMIN / "omnimind_bug_triage_utility.py")
        out = subprocess.run([sys.executable, tool, "--db", str(self.db), "summary"], capture_output=True,
                             text=True, env=env, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("Bug reports: 5  verified: 5  invalid: 0", out.stdout)
        out = subprocess.run([sys.executable, tool, "--db", str(self.db), "list", "--limit", "2"],
                             capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.count("VERIFIED"), 2)
        out = subprocess.run([sys.executable, tool, "--db", str(self.db), "--json", "show", self.ids[0]],
                             capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertTrue(json.loads(out.stdout)["signature_ok"])
        out = subprocess.run([sys.executable, tool, "--db", str(self.db), "show", "0xnope"],
                             capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(out.returncode, 1)


REMOTE_IP = _local_ip()


@unittest.skipIf(REMOTE_IP.startswith("127."), "no non-loopback IP on this machine")
class RemoteHubBugReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="omni_bug_remote_"))
        cls.d = Daemon(cls.tmp, "remote", remote=True)
        cls.d.start()
        cls.token = (cls.d.home / ".omni" / "hub_token").read_text().strip()
        cls.remote = f"http://{REMOTE_IP}:{cls.d.ports['OMNI_IPC_PORT']}"

    @classmethod
    def tearDownClass(cls):
        cls.d.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_remote_post_requires_token(self):
        code, _ = _http(f"{self.remote}/api/bugs/report", SAMPLE)
        self.assertEqual(code, 401)
        code, _ = _http(f"{self.remote}/api/bugs/report", SAMPLE, headers={"Authorization": "Bearer wrong"})
        self.assertEqual(code, 401)
        code, body = _http(f"{self.remote}/api/bugs/report", SAMPLE,
                           headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(code, 200, body)
        _, lst = _http(f"{self.d.ipc}/api/bugs/list")
        mine = [r for r in lst["reports"] if r["event_id"] == body["event_id"]]
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0]["report"]["received_via"], "remote_hub")
        self.assertTrue(mine[0]["verified"])

    def test_remote_validation_and_size_cap_still_apply(self):
        auth = {"Authorization": f"Bearer {self.token}"}
        code, _ = _http(f"{self.remote}/api/bugs/report", {"app": "KickBack"}, headers=auth)
        self.assertEqual(code, 400)
        code, _ = _http(f"{self.remote}/api/bugs/report", None, headers=auth,
                        raw=json.dumps({"what_happened": "q" * 9000}).encode())
        self.assertEqual(code, 413)

    def test_remote_list_is_loopback_only(self):
        code, _ = _http(f"{self.remote}/api/bugs/list", headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
